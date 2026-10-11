# librephoto

[LibrePhotos](https://github.com/LibrePhotos/librephotos): self-hosted photo library over the NAS photo folders. It runs as four components: backend (Django API + workers), frontend, nginx proxy and redis. The ML features (faces, captioning, scenes, LLM, geocoding) are disabled to keep memory usage low.

- **Namespace:** `librephoto` (PSS enforce `baseline`, warn `restricted`)
- **URLs:** `https://photo.internal.fferrando.cc` (LAN), `https://photo.fferrando.cc` (Cloudflare tunnel, rate-limited)
- **Database:** `librephoto` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `librephoto-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | The same credentials sealed for `librephoto`. |
| `secret-key.yaml` | 0 | SealedSecret `librephoto-secret-key` (`secret-key`): the Django `SECRET_KEY`. |
| `config_volume.yaml` | 0 | `librephoto-protected-media` PVC (10Gi, `longhorn-single-replica`, RWX) for thumbnails and generated media, shared by backend and proxy. |
| `nfs_volume.yaml` | 0 | Static NFS PV + PVC `librephoto-nfs-data` pointing at `192.168.10.101:/mnt/vault/data`. `Filippo/Foto` and `Famiglia/Foto` are mounted as subPaths under `/data`. |
| `certificate.yaml` | 2 | cert-manager Certificate for `photo.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `librephoto`. |
| `backend.yaml` | 5 | Backend Deployment + Service (8001). DB, redis, CSRF origins, 1 worker, logs in `/tmp/logs`. |
| `frontend.yaml` | 5 | Frontend Deployment + Service (3000), pinned to the backend's node with pod affinity. |
| `proxy.yaml` | 5 | nginx proxy Deployment + Service (80), pinned to the backend's node, serving `/protected_media` and the photo folders directly. Also defines the `backend` and `frontend` Service aliases, because the proxy image's nginx config expects upstreams with those exact names. |
| `redis.yaml` | 5 | Redis Deployment + Service (6379) for the job queue and cache. |
| `ingressroute.yaml` | 6 | Internal and public routes to `librephoto-proxy`, plus `public-ratelimit`. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace, CNPG and the public internet. |
