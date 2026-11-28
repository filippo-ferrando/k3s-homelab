# forgejo-runner

Forgejo Actions runners on the cluster, autoscaled by [KEDA](../../infrastructure/keda). KEDA polls Forgejo for pending jobs with the `docker` label and starts one Kubernetes Job per pending job. Each Job runs `forgejo-runner one-job`: it takes one CI job, runs it in a Docker-in-Docker sidecar and exits. No runner pods run while the queue is empty; only the small shared cache server stays up.

The external VM runner stays registered with the same label. A job runs on whichever runner takes it first.

- **Namespace:** `forgejo-runner` (PSS enforce `privileged`, warn `restricted`)
- **Runner:** `code.forgejo.org/forgejo/runner` 13, one shared runner identity named `k3s`
- **Label:** `docker:docker://data.forgejo.org/oci/node:22-bookworm`
- **Dashboard:** "Forgejo CI Runners" row in the Grafana overview dashboard

## Limits

| Setting | Value | Where |
|---|---|---|
| Parallel runners | 4 | `ScaledJob.spec.maxReplicaCount` |
| CPU per runner | 4 cores (request 1) | `dind` container limits |
| Memory per runner | 4Gi (request 1Gi) | `dind` container limits |
| Docker storage per runner | 20Gi | `docker-data` emptyDir `sizeLimit` |
| Job timeout | 3h | runner `timeout` and Job `activeDeadlineSeconds` |
| Actions cache storage | 20Gi, shared | `forgejo-runner-cache` PVC (`longhorn-single-replica`) |

Every CI job container is started by the pod's DinD daemon, so the `dind` container limits cap the whole CI job. A process that pushes the job over 4Gi is OOM-killed inside the job (`dind` keeps running; the dashboard counts it from `container_oom_events_total`). The runner container itself is limited to 256Mi.

This depends on the cgroup setup in the `dind` command. Privileged containers on these nodes share the host cgroup namespace, so a plain `dockerd` creates CI containers in `/sys/fs/cgroup/docker` at the node root, outside the pod and without any limit (this happened on the first runs). The `dind` command instead moves dockerd into `<container cgroup>/dockerd` and starts CI containers with `--cgroup-parent=<container cgroup>/ci`, so they are children of the pod's cgroup. It runs `dockerd` through `docker-init` directly, not through the image entrypoint, whose cgroup v2 setup moves processes at the host cgroup root into `/init`.

Check on a node while a CI job runs: `/sys/fs/cgroup/docker` must not gain children, and `kubectl top pod -n forgejo-runner` must show the job's CPU on the `dind` container.

## How a pod runs

1. KEDA reads `/api/v1/admin/runners/jobs?labels=docker` every 15s with the `api-token`. For N pending jobs it creates up to N Jobs, minus the runner Jobs already active, capped at 4.
2. `dind` starts as a native sidecar (init container with `restartPolicy: Always`). It listens only on `unix:///run/docker/docker.sock` in an emptyDir shared with the runner (group 1000, no TCP, no TLS). The runner starts after the sidecar's `docker info` startupProbe passes.
3. `runner` runs `forgejo-runner one-job` against `http://forgejo.forgejo.svc.cluster.local:3000`. Job containers get the DinD socket at `/var/run/docker.sock`, so `docker build` works inside workflows.
4. The runner exits after the job, and the kubelet then stops `dind`. Exit code 2 (no task, because the VM runner took the job first) is mapped to success. KEDA deletes succeeded Jobs on its next poll and keeps the last 2 failed ones for `kubectl logs`; `ttlSecondsAfterFinished: 600` removes anything left after 10 minutes. CI job logs are in Forgejo.

The ScaledJob uses `rollout.strategy: gradual`: a change to it (a push, a Renovate bump) leaves running Jobs alone. With the default `immediate`, KEDA deletes running Jobs and their CI jobs stay "running" in Forgejo until `ZOMBIE_TASK_TIMEOUT` (default 10m).

The Forgejo jobs endpoint returns both waiting and running jobs. KEDA subtracts its running Jobs, so a running CI job does not start an extra pod. A CI job whose runner pod died (orphaned task) does: KEDA starts pods every poll that exit with "no task received" until Forgejo fails the task or the run is cancelled.

DinD uses MTU 1400 (also for the per-job networks), below the flannel VXLAN MTU of 1450. With the default 1500, large TLS transfers from job containers stall.

## Actions cache

`actions/cache` works across runner pods through one shared cache server (`cache-server.yaml`). Without it, each pod ran its own internal cache server on the `runner-data` emptyDir, so every cache saved by a job was lost at pod exit and every restore missed.

- Each runner pod runs the runner's local cache proxy and gives it to the job as `ACTIONS_CACHE_URL`. Job containers reach the proxy on the pod IP inside the pod network namespace, so the network policy does not apply to this hop.
- The proxy forwards to `cache.external_server` (`http://forgejo-runner-cache.forgejo-runner.svc.cluster.local:4001/`). With `external_server` set, the runner pods do not start an internal cache server.
- The Deployment `forgejo-runner-cache` runs `forgejo-runner cache-server` with the same `config.yml`; it reads `cache.dir` (`/cache`) and `cache.port` (4001) from it.
- Proxy and server authenticate with the shared runner secret (`token` key of `forgejo-runner-credentials`), loaded with `cache.secret_url: file:/secrets/token` in both pods. No separate cache secret.
- Data lives on a 20Gi `longhorn-single-replica` PVC: the cache is rebuildable, a lost volume only costs cache misses. The Deployment uses `Recreate` because the volume is RWO.
- Retention is the server's built-in GC: only the newest entry per cache key is kept, and entries unused for 7 days are removed. Keys that include `hashFiles()` create new entries on each lockfile change; the old ones expire after 7 days.
- If the cache server is down, `actions/cache` logs a warning and the job continues.

The external VM runner keeps its own local cache.

## Container registry

Workflows log in to and push to the Forgejo registry at `git.internal.fferrando.cc`. Inside the cluster this hostname resolves to the ServiceLB node IPs (`192.168.10.100-103`). kube-proxy DNATs that traffic to a Traefik pod on `websecure` (8443) before the network policy is evaluated, so the egress rule targets the Traefik pods on 8443, not the node IPs. Without it, `docker login` fails with `dial tcp 192.168.10.101:443: connect: connection refused` (kube-router rejects the packet). The rule exposes every `*.internal` route on Traefik to CI jobs, but not the nodes, the NAS or other pods directly.

kube-router applies the policy to a new pod about 20 seconds after it starts. Connectivity tests from a fresh pod must wait for that, or they pass against an unfiltered pod.

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace, PSS `privileged` for the DinD sidecar. |
| `secrets.yaml` | 0 | SealedSecret `forgejo-runner-credentials`: `uuid` and `token` (runner identity) and `api-token` (Forgejo admin token for KEDA). Created by hand, see below. |
| `config.yaml` | 0 | ConfigMap `forgejo-runner-config`: runner `config.yml` (capacity 1, label, external cache server, `docker_host` socket), also read by the cache server. The server connection is passed on the command line. |
| `cache-server.yaml` | 3 | PVC (`longhorn-single-replica`, 20Gi), Deployment and Service `forgejo-runner-cache`: shared `actions/cache` server on 4001. |
| `scaledjob.yaml` | 5 | `TriggerAuthentication` `forgejo-runner-creds` and `ScaledJob` `forgejo-runner` (trigger `forgejo-runner`, global scope, label `docker`). |
| `networkpolicy.yaml` | - | No ingress, except runner pods to the cache server on 4001. Egress to DNS, Forgejo on 3000, the cache server on 4001, the Traefik pods on 8443 (registry) and the public internet (not the LAN, nodes, pods or tailnet). Also applies to the CI job containers. |

**Prerequisites:** KEDA (`infrastructure/keda`), and the ingress entries for the `forgejo-runner` and `keda` namespaces in `apps/forgejo/networkpolicy.yaml`.

**Policy exceptions:** `ScaledJob/forgejo-runner/forgejo-runner` is in `ALLOW_PRIVILEGED` in `ci/check_manifests.py`.

**Falco exceptions:** `rules-forgejo-runner.yaml` in `infrastructure/falco/values.yaml`. CI job containers have no k8s metadata in Falco and are matched by their cgroup path, which ends in `.scope/ci/<docker id>` because of the `--cgroup-parent` above. Changing the `ci` cgroup name in the `dind` command breaks the Falco exceptions; update the `forgejo_runner_ci_container` macro with it. See the [Falco README](../../infrastructure/falco/README.md#forgejo-runner-exceptions).

## One-time setup

The runner is registered offline with a shared secret, so pods never call the registration API. Forgejo derives the runner UUID from the first 16 characters of the secret, and the token is the full secret.

```bash
SECRET=$(openssl rand -hex 20)

# Register the runner in Forgejo (empty scope = instance-wide). Forgejo refuses to run as root.
kubectl exec -n forgejo deploy/forgejo -- su-exec git \
  forgejo --config /data/gitea/conf/app.ini forgejo-cli actions register \
  --name k3s --secret "$SECRET" --labels docker

# Derive the UUID the runner must present
UUID=$(docker run --rm code.forgejo.org/forgejo/runner:13.2.2 sh -c \
  "cd /tmp && forgejo-runner create-runner-file --instance http://x --name k3s --secret $SECRET >/dev/null 2>&1 && sed -n 's/.*\"uuid\": \"\(.*\)\".*/\1/p' .runner")
echo "$UUID"
```

Create a Forgejo access token for KEDA with an admin account: Settings > Applications > Generate new token, scope `read:admin`. Then seal all three values:

```bash
kubectl create secret generic forgejo-runner-credentials \
  --namespace forgejo-runner \
  --from-literal=uuid="$UUID" \
  --from-literal=token="$SECRET" \
  --from-literal=api-token="<KEDA_TOKEN>" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > apps/forgejo-runner/secrets.yaml
```

Add `argocd.argoproj.io/sync-wave: "0"` to the SealedSecret metadata and commit it.

## Changing the labels

The label lives in two places that must stay in sync: `runner.labels` in `config.yaml` (full `name:docker://image` form) and the trigger `labels` in `scaledjob.yaml` (name only, comma separated). The registration `--labels` is overwritten by the runner on its first connection.

## Checks

```bash
kubectl get scaledjob -n forgejo-runner              # READY and ACTIVE
kubectl get jobs,pods -n forgejo-runner -w           # at most 4 active Jobs
kubectl logs -n forgejo-runner job/<job> -c runner   # CI job log as seen by the runner
kubectl logs -n keda deploy/keda-operator | grep forgejo   # scaler errors (token, URL)
kubectl logs -n forgejo-runner deploy/forgejo-runner-cache # cache server
kubectl exec -n forgejo-runner deploy/forgejo-runner-cache -- du -sh /cache   # cache size
```
