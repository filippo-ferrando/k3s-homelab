# vibravid

[vibravid](https://github.com/astraelabs/vibravid): web video downloader. It writes straight into the `TV` folder of the media share, so downloads show up in Jellyfin.

- **Namespace:** `vibravid` (PSS `restricted`)
- **URL:** `https://download.internal.fferrando.cc` (LAN only)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `config_volume.yaml` | 0 | `vibravid-config` PVC (1Gi, `longhorn-single-replica`). Holds the SQLite DB and Django secret key (`data/`), `config.toml` and `login.toml` (`Conf/`), logs and service tokens (`cache/`), and the downloaded ffmpeg/velora/flux tools (`binary/`, about 340M). |
| `nfs_volume.yaml` | 0 | Static NFS PV + PVC `vibravid-data` pointing at `192.168.10.101:/mnt/media`. Only the `TV` subPath is mounted at `/downloads`. |
| `certificate.yaml` | 2 | cert-manager Certificate for `download.internal.fferrando.cc`. |
| `deployment.yaml` | 5 | Single replica (`Recreate`), non-root (uid 1000, gid 999, the image's `appuser`), all capabilities dropped. The image entrypoint needs root for PUID remapping and `gosu`, so `command` runs its last two steps directly: `migrate`, then `runserver`; velora and flux are downloaded lazily instead of pre-fetched. `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` are set to the internal host, and the output dir is set via `VIBRAVID_OUTPUT_ROOT`. Read-only root filesystem: the `vibravid-config` subPaths are mounted at `/app/data`, `/app/Conf`, `/app/.cache` and `/home/appuser/.local/bin/binary` (the paths the upstream `docker-compose.yml` persists), `/tmp` is an emptyDir and `PYTHONDONTWRITEBYTECODE=1`. Service plugins uploaded from the web UI cannot be installed, since `/app/VibraVid/services` is not writable. |
| `service.yaml` | 5 | ClusterIP on 8000. |
| `ingressroute.yaml` | 6 | Internal route only. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace and the public internet (video sources). |
