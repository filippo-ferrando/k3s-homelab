# longhorn

[Longhorn](https://longhorn.io) distributed block storage. It backs every non-NFS PVC. Synced first (wave -4) together with sealed-secrets, because almost everything else needs volumes.

- **Namespace:** `longhorn-system`
- **URL:** `https://longhorn.internal.fferrando.cc` (LAN only, basic auth)

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -4 | Argo CD Application for the `longhorn` chart, with values from this repo. |
| `values.yaml` | - | Chart ingress disabled (Traefik is used instead). Default 3 replicas, drain policy `always-allow`, auto-delete pods whose volume detached unexpectedly, pre-upgrade checker job enabled, ServiceMonitor enabled. |
| `storageclass-single.yaml` | -1 | `longhorn-single-replica` StorageClass (1 replica, expandable). Used by workloads that replicate themselves (CNPG) or whose data is disposable/rebuildable (Prometheus, Grafana, Alertmanager, caches). |
| `sealed-longhorn-auth.yaml` | -1 | SealedSecret `longhorn-auth-secret` (`users`, htpasswd format) for the UI. |
| `middleware.yaml` | 2 | Traefik `basicAuth` middleware `longhorn-auth` using that secret. |
| `certificate.yaml` | 2 | Certificate for `longhorn.internal.fferrando.cc`. |
| `ingressroute.yaml` | 2 | Internal route to `longhorn-frontend` behind `longhorn-auth`. |
| `networkpolicyprom.yml` | 2 | Lets Prometheus scrape `longhorn-manager` on 9500. |

**Host prerequisites** (iSCSI, NFS client, etc.) are installed by `ansible/provision/01_os.yml`.
