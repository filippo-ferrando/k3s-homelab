# forgejo-runner

Forgejo Actions runners on the cluster, autoscaled by [KEDA](../../infrastructure/keda). KEDA polls Forgejo for pending jobs with the `docker` label and starts one Kubernetes Job per pending job. Each Job runs `forgejo-runner one-job`: it takes one CI job, runs it in a Docker-in-Docker sidecar and exits. No pods run while the queue is empty.

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

Every CI job container is started by the pod's DinD daemon, so the `dind` container limits cap the whole CI job. A job that exceeds 4Gi is OOM-killed. The runner container itself is limited to 256Mi.

## How a pod runs

1. KEDA reads `/api/v1/admin/runners/jobs?labels=docker` every 15s with the `api-token`. For N pending jobs it creates up to N Jobs, minus the runner Jobs already active, capped at 4.
2. `dind` starts as a native sidecar (init container with `restartPolicy: Always`). It listens only on `unix:///run/docker/docker.sock` in an emptyDir shared with the runner (group 1000, no TCP, no TLS). The runner starts after the sidecar's `docker info` startupProbe passes.
3. `runner` runs `forgejo-runner one-job` against `http://forgejo.forgejo.svc.cluster.local:3000`. Job containers get the DinD socket at `/var/run/docker.sock`, so `docker build` works inside workflows.
4. The runner exits after the job, and the kubelet then stops `dind`. Exit code 2 (no task, because the VM runner took the job first) is mapped to success. Finished Jobs are deleted after 1h; KEDA keeps the last 5 succeeded and 5 failed.

DinD uses MTU 1400 (also for the per-job networks), below the flannel VXLAN MTU of 1450. With the default 1500, large TLS transfers from job containers stall.

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace, PSS `privileged` for the DinD sidecar. |
| `secrets.yaml` | 0 | SealedSecret `forgejo-runner-credentials`: `uuid` and `token` (runner identity) and `api-token` (Forgejo admin token for KEDA). Created by hand, see below. |
| `config.yaml` | 0 | ConfigMap `forgejo-runner-config`: runner `config.yml` (capacity 1, label, cache, `docker_host` socket). The server connection is passed on the command line. |
| `scaledjob.yaml` | 5 | `TriggerAuthentication` `forgejo-runner-creds` and `ScaledJob` `forgejo-runner` (trigger `forgejo-runner`, global scope, label `docker`). |
| `networkpolicy.yaml` | - | No ingress. Egress to DNS, Forgejo on 3000 and the public internet (not the LAN, nodes, pods or tailnet). Also applies to the CI job containers. |

**Prerequisites:** KEDA (`infrastructure/keda`), and the ingress entries for the `forgejo-runner` and `keda` namespaces in `apps/forgejo/networkpolicy.yaml`.

**Policy exceptions:** `ScaledJob/forgejo-runner/forgejo-runner` is in `ALLOW_PRIVILEGED` in `ci/check_manifests.py`.

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
```
