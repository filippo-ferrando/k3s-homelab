# kubecraft

On-demand Minecraft servers managed by kubecraft. The workload comes from its own Helm chart (published on the Forgejo OCI registry). This folder holds the Argo CD Application, its values, and everything the chart expects to already exist.

- **Namespace:** `minecraft` (PSS `restricted`)
- **UI:** `https://mine.fferrando.cc` (Cloudflare tunnel)
- **Game servers:** `<name>.mine.internal.fferrando.cc` through mc-router (LoadBalancer) on the LAN, and through playit.gg from the internet
- **Database:** `kubecraft` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | - | SealedSecret `kubecraft-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | - | The same credentials sealed for `minecraft`, referenced by `database.credentialsSecret`. |
| `secrets.yaml` | - | SealedSecret `kubecraft-secrets`: `BOOTSTRAP_ADMIN_USER`, `BOOTSTRAP_ADMIN_PASSWORD`, `SESSION_SECRET`. |
| `playit_secret.yaml` | - | SealedSecret `kubecraft-playit` (`SECRET_KEY`): the playit.gg agent key. playit exposes game ports publicly, because the Cloudflare tunnel can't carry raw TCP. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `kubecraft`. |
| `application.yaml` | 5 | Argo CD Application: chart `kubecraft` from `git.fferrando.cc/rdfilippo` (OCI), with values from this repo (multi-source `$values`). |
| `values.yaml` | - | Chart values: UI host and server base domain, `longhorn-single-replica` for world storage, max 2 servers per user, DB settings (`sslmode=require`), mc-router as a LoadBalancer with autoscale down after 15m, playit enabled, ServiceMonitor, and NetworkPolicy sources (Traefik for the UI, monitoring for metrics). The chart's own IngressRoute and Certificate are disabled. |
| `ingressroute.yaml` | 6 | Public route to the chart's `kubecraft` service, with a strict rate limit (10/min) on `/api/auth/login` only, because the UI polls the API and would hit a site-wide limit. |

**Prerequisites:** the Forgejo OCI repository secret (`infrastructure/lastgasp/repository.yaml`), and a 5432 allow entry for `app.kubernetes.io/name: kubecraft-manager` in `apps/database/networkpolicy.yaml` (the manager only, since game servers run user code). Grafana dashboard: `infrastructure/kube-prometheus-stack/dashboard-kubecraft.yaml`.
