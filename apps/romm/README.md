# romm

[RomM](https://github.com/rommapp/romm): ROM manager. It scans the ROM library on the NAS, enriches it with metadata and artwork, and plays games in the browser.

- **Namespace:** `romm` (PSS `restricted`)
- **URL:** `https://rom.internal.fferrando.cc` (LAN only)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `romm-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | SealedSecret `romm-db-credentials` in `romm`, read by the pod. |
| `secrets.yaml` | 0 | SealedSecret `romm-secrets` with `ROMM_AUTH_SECRET_KEY`. |
| `pvc.yaml` | 0 | `romm-data` PVC (10Gi, `longhorn`, RWO). Holds covers and screenshots (`resources/`), uploaded saves and states (`assets/`), `config.yml` (`config/`) and the internal Valkey snapshot (`redis-data/`). |
| `nfs_volume.yaml` | 0 | Static NFS PV + PVC `romm-data-nfs` pointing at `192.168.10.101:/mnt/vault/data` (same export as Filebrowser). Only the `Filippo/Games/Roms` and `Filippo/Games/Bios` subPaths are mounted. |
| `certificate.yaml` | 2 | cert-manager Certificate for `rom.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` `romm` and `Database` `romm` on `homelab-db`. |
| `deployment.yaml` | 5 | Single replica (`Recreate`, since the data PVC is RWO), non-root (uid/gid 1000, the image's `romm` user, `fsGroup: 1000`), all capabilities dropped. Image pinned to `rommapp/romm:5.4.1`. Uses CNPG through `ROMM_DB_DRIVER=postgresql` instead of the upstream MariaDB, and the Valkey built into the image. `ROMM_BASE_URL` is the internal host and the session cookie is `Secure`. Keyless metadata providers enabled: Hasheous, LaunchBox, PlayMatch. `SCAN_WORKERS` and `WEB_SERVER_CONCURRENCY` are 4 (upstream values). Library in structure A: `Filippo/Games/Roms` (platform folders) at `/romm/library/roms`, read-write, and `Filippo/Games/Bios` at `/romm/library/bios`. Read-only root filesystem: the `romm-data` subPaths are mounted at `/romm/resources`, `/romm/assets`, `/romm/config` and `/redis-data` (the paths the upstream `docker-compose.yml` persists), `/etc/nginx/conf.d` is an emptyDir for the rendered nginx templates, `/tmp` is a 10Gi emptyDir (pid files and the zip/conversion cache under `/tmp/romm`). Readiness and liveness probes on `/api/heartbeat`. `enableServiceLinks: false`: otherwise the `romm` Service injects `ROMM_PORT=tcp://<ip>:8080`, which RomM reads as its listen port, and nginx fails to start. |
| `service.yaml` | 5 | ClusterIP on 8080. |
| `ingressroute.yaml` | 6 | Internal route only. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace, `homelab-db` on 5432 and the public internet (metadata providers). |

**Prerequisites:**
- The NFS exports on casper (`ansible/provision/06_nfs.yml`).
- The folders `Filippo/Games/Roms` and `Filippo/Games/Bios` on the `data` share, readable and writable by uid 1000.
- The sealed secrets above. Recipes: [`notes/kubectl.md`](../../notes/kubectl.md#sealed-secrets).

**First login:** the setup wizard creates the admin user on the first visit.
