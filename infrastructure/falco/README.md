# falco

[Falco](https://falco.org) runtime intrusion detection on every node (control plane included), with Falcosidekick for alert fan-out and metrics in Prometheus.

- **Namespace:** `falco`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | 1 | Argo CD Application for the `falcosecurity/falco` chart, with values from this repo (multi-source `$values`). |
| `values.yaml` | - | `modern_ebpf` driver, control-plane tolerations, ServiceMonitors for Falco and Falcosidekick, resource limits, and custom rules that silence known-good behaviour (see below). |

## Testing a rule change

Validate the rule files and run a throwaway Falco next to the real one before pushing. Copy the files with a tar stream; piping single files through `kubectl exec -i ... cat >` can leave them empty without an error. Keep output files outside the rules directory, since Falco loads every file in it.

```bash
mkdir -p /tmp/rules.d && python3 -c '
import yaml
for k, c in yaml.safe_load(open("infrastructure/falco/values.yaml"))["customRules"].items():
    open(f"/tmp/rules.d/{k}", "w").write(c)'
P=$(kubectl -n falco get pod -l app.kubernetes.io/name=falco --field-selector spec.nodeName=<node> -o name)
kubectl -n falco exec $P -c falco -- mkdir -p /tmp/rtest
tar -C /tmp/rules.d -cf - . | kubectl -n falco exec -i $P -c falco -- tar -C /tmp/rtest -xf -
kubectl -n falco exec $P -c falco -- sh -c 'timeout 120 falco -c /etc/falco/falco.yaml \
  -r /etc/falco/falco_rules.yaml -r /tmp/rtest -o webserver.enabled=false -o metrics.enabled=false \
  -o http_output.enabled=false -o json_output=true; rm -rf /tmp/rtest'
```

## Custom rules in `values.yaml`

| Rule file | What it allows |
|---|---|
| `rules-cnpg-wal.yaml` | Postgres in `database` running `/controller/manager wal-archive`/`wal-restore` via `sh -c` (no shell metacharacters allowed). |
| `rules-k8s-api.yaml` | Controllers that legitimately talk to the k8s API: Argo CD, Dex, cert-manager, the CNPG operator and instance manager, KEDA (operator, admission webhooks, metrics apiserver), Longhorn manager and CSI sidecars, kube-state-metrics, Traefik. Matched by namespace + image + executable path. |
| `rules-forgejo-sshd.yaml` | Forgejo's sshd on port 22 from the pod network, and Longhorn instance-manager stream redirects. |
| `rules-forgejo-binary.yaml` | Forgejo executing `/app/gitea/gitea` (avoids a "Drop and execute" false positive). |
| `rules-forgejo-runner.yaml` | Forgejo Actions runner pods (`apps/forgejo-runner`), see below. |

Each exception is scoped as narrowly as possible (namespace, image, uid, binary). Extend these rules instead of disabling them.

## Forgejo runner exceptions

CI job containers are started by the DinD sidecar of a runner pod, not by the kubelet, so Falco has no namespace, pod or image for them (`k8s.ns.name` and `container.image.repository` are `<NA>`). The macro `forgejo_runner_ci_container` identifies them by cgroup instead: dockerd runs with `--cgroup-parent=<dind container cgroup>/ci`, so every CI container lives under `/kubepods.slice/.../cri-containerd-<id>.scope/ci/<docker id>`. No kubelet-managed container has a `ci` level below its scope.

| Rule | Exception |
|---|---|
| Drop and execute new binary in container | Any process in a CI container (`known_drop_and_execute_activities`, appended). CI jobs install toolchains under `/opt/hostedtoolcache`, compile and run test binaries and install packages. |
| Read sensitive file untrusted | `/usr/bin/systemd-sysusers` reading `/etc/shadow` or `/etc/gshadow` in a CI container (apt-get installing a package that creates users). |
| Clear Log Activities | `dockerd` in the `dind` container truncating files under `/var/lib/docker/` (image layers that ship `/var/log/dpkg.log`). |
| Packet socket created in container | `dockerd` in the `dind` container opening an `AF_PACKET` socket (gratuitous ARP when a container joins a bridge network). Rule condition appended, since the stock rule has no exception macro. |

The CI exception is broad by design: CI jobs run repository code that downloads and executes binaries, so Falco cannot tell a CI job from an attack inside a CI container. Falco still sees everything outside the `ci` cgroup, including the `dind` and `runner` containers and the node. The runner's network policy and the DinD resource limits contain the CI jobs.

`rules-forgejo-runner.yaml` must sort after `rules-forgejo-binary.yaml`: `rules.d` is loaded in alphabetical order, and its append to `known_drop_and_execute_activities` must land on top of the `replace` there.
