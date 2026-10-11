# cloudflared

Cloudflare Tunnel connector: the only path from the internet into the cluster. Cloudflare terminates TLS and forwards traffic over plain HTTP to Traefik's `cf-public` entrypoint (9443), where the public IngressRoutes live. The hostname-to-service mapping is configured remotely in the Cloudflare Zero Trust dashboard (token-based tunnel).

- **Namespace:** `cloudflared` (PSS `restricted`)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `sealed-tunnel-token.yaml` | -1 | SealedSecret `tunnel-token` (key `token`). |
| `deployment.yaml` | 0 | `cloudflared tunnel run` as non-root (uid 65532), all capabilities dropped, metrics and readiness on `:2000`. Uses `--no-autoupdate`: the version is pinned by image tag and bumped by Renovate, and self-update triggered Falco's "Drop and execute" rule. |
| `networkpolicy.yaml` | - | No ingress. Egress only to DNS, Traefik on 9443 and public IPs on 7844 (tunnel, QUIC/HTTP2) and 443 (Cloudflare API). |
