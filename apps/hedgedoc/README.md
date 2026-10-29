# hedgedoc

[HedgeDoc](https://hedgedoc.org): collaborative Markdown notes. Anonymous access and email registration are disabled, and notes default to `private`.

- **Namespace:** `hedgedoc` (PSS `restricted`)
- **URL:** `https://doc.fferrando.cc` (Cloudflare tunnel only, no internal route)
- **Database:** `hedgedoc` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `hedgedoc-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | The same credentials sealed for the `hedgedoc` namespace. |
| `pvc.yaml` | 0 | `hedgedoc-uploads` PVC (5Gi, default StorageClass) for uploaded images. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `hedgedoc`. |
| `deployment.yaml` | 5 | HedgeDoc 1.12 (`Recreate`, non-root uid 10000, `fsGroup: 10000`, all capabilities dropped), configured via `CMD_*` env vars, with readiness and liveness probes on `/_health`. Read-only root filesystem, `/tmp` is an emptyDir. |
| `service.yaml` | 5 | ClusterIP on 3000. |
| `ingressroute.yaml` | 5, 6 | `hedgedoc-headers` middleware (forces `X-Forwarded-Proto: https`, because TLS ends at Cloudflare and HedgeDoc would otherwise build `http://` URLs), the public IngressRoute and `public-ratelimit`. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace and CNPG on 5432 only. |
