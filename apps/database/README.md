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
| `networkpolicy.yaml` | - | Ingress allowlist: instance-to-instance replication (also admits the backup Jobs, which run in this namespace); CNPG operator on 8000; Prometheus on 9187 (postgres exporter); 5432 only from the specific client pods (forgejo, hedgedoc, vaultwarden, jellyfin, librephoto-backend, lastgasp server, kubecraft manager). |
| `backup_secret.yaml` | 0 | SealedSecret `backup-db-credentials` (`kubernetes.io/basic-auth`, user `backup`, random password), used by the `backup` role and the `pg-backup` CronJob. |
| `backup_volume.yaml` | 0 | PV/PVC `pg-backups-nfs`: NFS `192.168.10.101:/mnt/vault/data/backups/pg_db`, `ReadWriteMany`, `Retain`. |
| `backup_scripts.yaml` | 0 | ConfigMap `pg-backup-scripts` with `backup.sh` and `restore-test.sh`, mounted at `/scripts`. |
| `backup_role.yaml` | 3 | `DatabaseRole` `backup`: login, member of `pg_read_all_data` (read-only on every database), connection limit 3. |
| `backup_cronjob.yaml` | 5 | CronJob `pg-backup`: weekly dump of every database to the NFS PVC. |
| `restore_test_cronjob.yaml` | 5 | CronJob `pg-restore-test`: weekly restore of the newest backup into a throwaway Postgres, with a row-count check. |

## Adding a new app database

1. In the app folder, create `db_secret.yaml`: a SealedSecret in the `database` namespace with `username`/`password`, labelled `cnpg.io/reload: "true"`.
2. Create `deployment_secret.yaml`: the same credentials sealed for the app's namespace.
3. Create `db.yaml`: a CNPG `DatabaseRole` (wave 3) and a `Database` (wave 4) pointing at `homelab-db`.
4. Add the app pod's namespace and label to the 5432 rule in `networkpolicy.yaml` here, and add an egress rule to `database` in the app's own NetworkPolicy.

## Backup and restore test

Weekly logical backups (`pg_dump`) on an NFS share, plus a weekly job that proves the newest backup restores.
CNPG's native backups were not used: the Barman Cloud plugin writes only to object stores (S3, Azure, GCS), and `volumeSnapshot` backups need the external-snapshotter and a Longhorn backup target, which this cluster does not run. Tradeoff: weekly copies only, no point-in-time recovery.

| CronJob | Schedule (Europe/Rome) | What it does |
|---|---|---|
| `pg-backup` | Sunday 05:30 | Connects to `homelab-db-rw` as `backup` (TLS). Dumps the globals (`pg_dumpall --globals-only --no-role-passwords`) and every database listed in `pg_database` at run time (`pg_dump -Fc`), so new app databases are included with no change here. Each database is dumped from an exported snapshot, and the exact row count of every table is recorded in the same snapshot. Keeps the newest 8 backups. |
| `pg-restore-test` | Sunday 06:30 | Takes the newest complete backup and checks its `SHA256SUMS`. Starts a throwaway Postgres in the pod (emptyDir, Unix socket only, no network) and restores the globals and every database. Fails if the backup is older than 8 days, if any `pg_restore` fails, if the set of databases differs, if a database other than `app_db` has no tables, or if any table's row count differs from the dump-time manifest. |

Both run outside the kured reboot window (01:00 to 05:00) as uid 26 under PSS `restricted`, with `concurrencyPolicy: Forbid` and no retries.

**Layout on NFS** (`casper:/mnt/vault/data/backups/pg_db`):

```
2026-11-22T053000/
  globals.sql        roles and memberships, without passwords (those are SealedSecrets in Git)
  databases.txt      databases in this backup
  <db>.dump          pg_dump custom format, restore with pg_restore
  <db>.counts        "schema.table<TAB>rows", taken in the dump's snapshot
  SHA256SUMS
  COMPLETE           written last; directories without it are ignored
.tmp-<timestamp>/    an interrupted run, deleted after one day
```

Files are mode 0644 on purpose: Borg on magi reads `/mnt/vault` through a `root_squash` export as an unprivileged user, so every dump also gets a copy in the Borg repository. Any local user on casper can read the dumps.

**Prerequisites:** the directory must exist and be owned by uid/gid 26 before the first sync (`ansible/provision/06_nfs.yml` creates it). kubelet fails the mount if it is missing, and `fsGroup` has no effect on NFS.

**Image and major version:** both CronJobs use the cluster's image, `ghcr.io/cloudnative-pg/postgresql:18.4-system-trixie`. `pg_dump` must be at least the server's major version, so bump these images together with a major upgrade of the cluster.

**Permissions:** `pg_read_all_data` reads every table, view and sequence, but not large objects, and does not bypass row-level security. The cluster has neither today (checked 2026-11-16). If an app adds them, `pg_dump` fails and the job reports it. Then set `bypassrls: true` on the role (RLS) or switch to a superuser (large objects).

**Status:** the "Host & DB Backups (Borg / CNPG)" row of the Homelab Overview and public dashboards shows the last result, days since the last success, and the duration of both CronJobs, from kube-state-metrics:

```promql
max by (cronjob) (kube_cronjob_status_last_successful_time{namespace="database",cronjob=~"pg-backup|pg-restore-test"} >= bool kube_cronjob_status_last_schedule_time{namespace="database",cronjob=~"pg-backup|pg-restore-test"})
(time() - max by (cronjob) (kube_cronjob_status_last_successful_time{namespace="database",cronjob=~"pg-backup|pg-restore-test"})) / 86400
```

The status panel needs `lastScheduleTime`, which only scheduled runs set: it shows "no data" until the first Sunday run, even after manual runs.

Manual runs, logs, and restoring a database from a dump: `notes/kubectl.md#database-cnpg`.
