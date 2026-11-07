# Move the Borg backup from host cron to a Kubernetes CronJob

## Context

Today `ansible/provision/07_backups.yml` installs borg on magi, mounts casper's `/mnt/vault` read-only at `/mnt/casper-data`, and runs `ansible/scripts/borg_backup_personal.sh` from cron (`0 2 */2 * *`) into `/mnt/data/backup-casper`. Metrics go to the Pushgateway.

Goal: the same job (same source, same repo, same node) runs as a CronJob managed by Argo CD, with no host cron and no custom script. Metrics come from kube-state-metrics (decision confirmed).

**Answer: yes, it can be done.** The two tools that make it work:
- **borgmatic** (container image with borg 1.4.x): a declarative YAML config runs create, prune and compact. This replaces the script.
- **kube-state-metrics** (already part of kube-prometheus-stack): exposes `kube_cronjob_status_last_successful_time`, `kube_job_status_failed/succeeded`, and `kube_job_status_start_time/completion_time`. This replaces the Pushgateway pushes.

## New service: `apps/borg-backup/`

| File | Content |
|------|---------|
| `namespace.yaml` | `borg-backup`, PSA `enforce: privileged` (hostPath is not allowed at baseline/restricted). The pod itself still runs as non-root. |
| `nfs_volume.yaml` | PV/PVC `borg-casper-source`: NFS `192.168.10.101:/mnt/vault`, `ReadOnlyMany`, mountOptions `nfsvers=4.2,hard,timeo=600,retrans=5`, mounted `readOnly: true` in the pod. Same pattern as `apps/jellyfin/nfs_volume.yaml`. kubelet on magi does the mount, so the source IP is still magi's, and the existing export (`06_nfs.yml`, ro, root_squash) does not change. |
| `secret.yaml` | SealedSecret `BORG_PASSPHRASE` (the contents of `/home/magi/.bak_psw`). |
| `config.yaml` | ConfigMap with `config.yaml` for borgmatic. See below. |
| `cronjob.yaml` | CronJob `borg-casper`. See below. |
| `networkpolicy.yaml` | Default deny ingress and egress. The pod needs no network because kubelet mounts the NFS share. |
| `README.md` | Per CLAUDE.md. |

### borgmatic config (same behavior as the script)
```yaml
source_directories: [/mnt/casper-data]
repositories: [{path: /mnt/data/backup-casper}]
exclude_patterns: ['**/appdata_*', '/mnt/casper-data/git/ssh/ssh_host_*']
compression: zstd
archive_name_format: 'magi-{now:%Y-%m-%dT%H:%M:%S}'   # matches existing {hostname} archives, so prune keeps grouping them
keep_daily: 5
keep_weekly: 3
keep_monthly: 3
encryption_passcommand: 'printenv BORG_PASSPHRASE'
```
(No `check` action. The script never ran one.)

### CronJob essentials
- `schedule: "0 2 */2 * *"`, `timeZone: Europe/Rome`, `concurrencyPolicy: Forbid`, `backoffLimit: 0`, `successfulJobsHistoryLimit: 1`, `failedJobsHistoryLimit: 1`.
- `nodeSelector: kubernetes.io/hostname: magi` plus a toleration for `node-role.kubernetes.io/control-plane:NoSchedule`.
- `hostname: magi` in the pod spec, so `{hostname}` and borg lock names stay the same.
- `securityContext`: `runAsUser`/`runAsGroup` = magi's uid/gid (check with `id magi`), `runAsNonRoot`, drop ALL capabilities. The repo files stay owned by magi, and root_squash reads keep working.
- The volumes are mounted at the **same paths as on the host**. Otherwise borg reports "repository moved" and the files cache misses, which makes it rehash all 2 TB:
  - NFS PVC to `/mnt/casper-data` (ro)
  - hostPath `/mnt/data/backup-casper` to `/mnt/data/backup-casper`
  - hostPath `/home/magi/.cache/borg` and `/home/magi/.config/borg` (reuse the existing files cache and security dir), via `BORG_CACHE_DIR`/`BORG_CONFIG_DIR`
  - emptyDir for `HOME` (borgmatic state)
- Image: `ghcr.io/borgmatic-collective/borgmatic:<pinned tag>`. The command is overridden to `borgmatic --verbosity 1 --list --stats`, which bypasses the image's built-in cron.

### kured interaction
kured reboots between 01:00 and 05:00, and the backup starts at 02:00 on magi. Add `blockingPodSelector: app=borg-backup` to `infrastructure/kured/values.yaml` so a node is not drained in the middle of a backup.

## Metrics / dashboards
Replace the Borg panels in `infrastructure/kube-prometheus-stack/dashboard-homelab-overview.yaml` and `dashboard-homelab-public.yaml`:
- Status: `kube_job_status_succeeded{namespace="borg-backup"}` (latest job), with failures from `kube_job_status_failed`
- Hours since last success: `(time() - kube_cronjob_status_last_successful_time{cronjob="borg-casper"}) / 3600`
- Duration: `kube_job_status_completion_time - kube_job_status_start_time` (namespace `borg-backup`)
- Drop the `backup_dump_bytes` query. Nothing in the repo pushes it.

## Removals
- `ansible/scripts/borg_backup_personal.sh`: delete.
- `ansible/provision/07_backups.yml`: replace with a one-shot cleanup (cron `state: absent`, remove `/usr/local/bin/borg-backup.sh`, unmount `/mnt/casper-data`). Then delete the playbook and the `borg_backup` inventory group. Keep the group if the NFS export in `06_nfs.yml` still references it. It does, so keep the group and drop only its comment about cron.
- `infrastructure/pushgateway/`: delete. Nothing else pushes to it.
- Keep `/home/magi/.bak_psw` on the host until the first in-cluster run succeeds.

## Docs to update
`ansible/README.md` (07, scripts, inventory rows), `infrastructure/pushgateway/README.md` (deleted), `infrastructure/kube-prometheus-stack/README.md`, `infrastructure/kured/README.md`, `notes/guides/bootstrap.md` (Pushgateway row), the root `README.md` if it lists services, `CHANGELOG.md`.

## Verification
1. On magi: `borg --version` (host) vs. the image's borg. Both must be 1.x. Run `id magi` for the uid/gid.
2. After the Argo sync: `kubectl -n borg-backup create job --from=cronjob/borg-casper manual-1`, then `kubectl logs -f`. Check that the run does not say "repository moved" or "unknown repository", and that the files cache makes the run short (not a full rehash).
3. `borg list /mnt/data/backup-casper` on magi: a new `magi-...` archive, and prune keeps the 5/3/3 retention.
4. Prometheus: `kube_cronjob_status_last_successful_time{cronjob="borg-casper"}` is populated, and the dashboard panels render.
5. Only then run the Ansible cleanup and delete the Pushgateway.
