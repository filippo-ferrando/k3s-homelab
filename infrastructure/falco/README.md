# falco

[Falco](https://falco.org) runtime intrusion detection on every node (control plane included), with Falcosidekick for alert fan-out and metrics in Prometheus.

- **Namespace:** `falco`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | 1 | Argo CD Application for the `falcosecurity/falco` chart, with values from this repo (multi-source `$values`). |
| `values.yaml` | - | `modern_ebpf` driver, control-plane tolerations, ServiceMonitors for Falco and Falcosidekick, resource limits, and custom rules that silence known-good behaviour (see below). |

## Custom rules in `values.yaml`

| Rule file | What it allows |
|---|---|
| `rules-cnpg-wal.yaml` | Postgres in `database` running `/controller/manager wal-archive`/`wal-restore` via `sh -c` (no shell metacharacters allowed). |
| `rules-k8s-api.yaml` | Controllers that legitimately talk to the k8s API: Argo CD, Dex, cert-manager, the CNPG operator and instance manager, Longhorn manager and CSI sidecars, kube-state-metrics, Traefik. Matched by namespace + image + executable path. |
| `rules-forgejo-sshd.yaml` | Forgejo's sshd on port 22 from the pod network, and Longhorn instance-manager stream redirects. |
| `rules-forgejo-binary.yaml` | Forgejo executing `/app/gitea/gitea` (avoids a "Drop and execute" false positive). |

Each exception is scoped as narrowly as possible (namespace, image, uid, binary). Extend these rules instead of disabling them.
