# vibravid

[vibravid](https://github.com/astraelabs/vibravid): web video downloader. It writes straight into the `TV` folder of the media share, so downloads show up in Jellyfin.

- **Namespace:** `vibravid` (PSS enforce `baseline`, warn `restricted`)
- **URL:** `https://download.internal.fferrando.cc` (LAN only)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `config_volume.yaml` | 0 | `vibravid-config` PVC (1Gi, `longhorn-single-replica`) for config, its SQLite DB and logs. |
| `nfs_volume.yaml` | 0 | Static NFS PV + PVC `vibravid-data` pointing at `192.168.10.101:/mnt/media`. Only the `TV` subPath is mounted at `/downloads`. |
| `certificate.yaml` | 2 | cert-manager Certificate for `download.internal.fferrando.cc`. |
| `deployment.yaml` | 5 | Single replica (`Recreate`). `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` are set to the internal host, and output/config/db/log dirs are set via `VIBRAVID_*` env vars. |
| `service.yaml` | 5 | ClusterIP on 8000. |
| `ingressroute.yaml` | 6 | Internal route only. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace and the public internet (video sources). |
