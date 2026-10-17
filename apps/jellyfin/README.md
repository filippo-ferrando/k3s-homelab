# jellyfin

[Jellyfin](https://jellyfin.org) media server, using the `jpvenson/jellyfin.pgsql` image so its library database lives on the shared Postgres instead of SQLite.

- **Namespace:** `jellyfin` (PSS enforce `baseline`, warn `restricted`)
- **URLs:** `https://jellyfin.internal.fferrando.cc` (homelab LAN, Tailscale and main home LAN), `https://jellyfin.fferrando.cc` (Cloudflare tunnel)
- **Database:** `jellyfin` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `jellyfin-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | The same credentials sealed for the `jellyfin` namespace. |
| `pvc.yaml` | 0 | `jellyfin-config` PVC (7Gi, `longhorn`, RWO) for `/config`. |
| `nfs_volume.yaml` | 0 | Static NFS PV + PVC `jellyfin-nfs` pointing at `192.168.10.101:/mnt/media`, mounted **read-only** at `/media`. |
| `certificate.yaml` | 2 | cert-manager Certificate for `jellyfin.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `jellyfin`. |
| `deployment.yaml` | 5 | Jellyfin (`Recreate`), Postgres via `POSTGRES_*` env vars, probes on `/health`, `emptyDir` for `/cache`. |
| `service.yaml` | 5 | ClusterIP on 8096. |
| `ingressroute.yaml` | 6 | Internal route (`websecure` + `home-lan`) and public route (`cf-public`). The public route uses a looser rate limit (600/min, burst 300) than the other apps, because streaming makes many requests. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace, CNPG and the public internet (metadata providers). |

Main home LAN setup (OPNsense port forward, DNS): `notes/guides/jellyfin_home_lan.md`.
