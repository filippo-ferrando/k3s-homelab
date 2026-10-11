# filebrowser_quantum

[FileBrowser Quantum](https://github.com/gtsteffaniak/filebrowser): web file manager over the NAS media and data shares.

- **Namespace:** `filebrowser` (PSS enforce `baseline`, warn `restricted`)
- **URLs:** `https://files.internal.fferrando.cc` (LAN), `https://files.fferrando.cc` (Cloudflare tunnel, rate-limited)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `config.yaml` | 0 | ConfigMap with FileBrowser's `config.yaml`: sources `/media` and `/data`, cache dir, admin username. |
| `config_volume.yaml` | 0 | `fbq-config` PVC (5Gi, `longhorn`, RWO) for FileBrowser's own database and cache. |
| `media_volume.yaml` | 0 | Static NFS PV + PVC `fbq-media-nfs` pointing at `192.168.10.101:/mnt/media`, mounted at `/media`. |
| `data_volume.yaml` | 0 | Static NFS PV + PVC `fbq-data-nfs` pointing at `192.168.10.101:/mnt/vault/data`, mounted at `/data`. |
| `internal-certificate.yaml` | 2 | cert-manager Certificate for `files.internal.fferrando.cc`. |
| `deployment.yaml` | 5 | Single-replica Deployment (`Recreate`, since the config PVC is RWO), `fsGroup: 1000`, readiness probe on `/healthcheck`. |
| `service.yaml` | 5 | ClusterIP on port 80. |
| `ingressroute.yaml` | 6 | Internal route (`websecure` + TLS), public route (`cf-public`) and the `public-ratelimit` middleware (60/min per `Cf-Connecting-Ip`). |
| `networkpolicy.yaml` | - | Ingress only from the namespace itself and Traefik. Egress only to DNS and the namespace's own pods. |

**Prerequisites:** the NFS exports on casper (`ansible/provision/06_nfs.yml`).
