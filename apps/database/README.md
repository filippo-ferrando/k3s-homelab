# database

Shared HA PostgreSQL cluster `homelab-db`, managed by the CloudNativePG operator (`infrastructure/cloudnative-pg`).
Every app that needs Postgres gets its own role and database on this cluster. Those are declared in the app's own folder (`db.yaml`), not here.

- **Namespace:** `database` (PSS `restricted`)
- **Endpoint for apps:** `homelab-db-rw.database.svc.cluster.local:5432` (read-write service, always points at the current primary)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | `database` namespace with Pod Security `restricted`. |
| `cluster.yaml` | 2 | CNPG `Cluster`: 3 instances with **required** anti-affinity (one per node), 15Gi each on `longhorn-single-replica` (CNPG replicates, so Longhorn doesn't need to), `primaryUpdateMethod: switchover` for zero-downtime rolling updates, PodMonitor enabled, `max_connections=300`, `shared_buffers=512MB`. Bootstraps a default `app_db`/`app_user`. |
| `networkpolicy.yaml` | - | Ingress allowlist: instance-to-instance replication; CNPG operator on 8000; Prometheus on 9187 (postgres exporter); 5432 only from the specific client pods (forgejo, hedgedoc, vaultwarden, jellyfin, librephoto-backend, lastgasp server, kubecraft manager). |

## Adding a new app database

1. In the app folder, create `db_secret.yaml`: a SealedSecret in the `database` namespace with `username`/`password`, labelled `cnpg.io/reload: "true"`.
2. Create `deployment_secret.yaml`: the same credentials sealed for the app's namespace.
3. Create `db.yaml`: a CNPG `DatabaseRole` (wave 3) and a `Database` (wave 4) pointing at `homelab-db`.
4. Add the app pod's namespace and label to the 5432 rule in `networkpolicy.yaml` here, and add an egress rule to `database` in the app's own NetworkPolicy.

Backup and restore: see `notes/kubectl.md#database-cnpg`.
