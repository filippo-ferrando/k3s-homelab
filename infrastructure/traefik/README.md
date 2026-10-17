# traefik

[Traefik](https://traefik.io) ingress controller, running as a DaemonSet. All routing uses `IngressRoute` CRDs, and cross-namespace references are disabled, so every namespace defines its own middlewares.

- **Namespace:** `traefik`
- **Dashboard:** `https://traefik.internal.fferrando.cc` (LAN only, basic auth)

## Entrypoints

| Name | Port | Use |
|---|---|---|
| `web` | 80 | Redirects to 443. |
| `websecure` | 443 (HTTP/3 on) | LAN routes, `*.internal.fferrando.cc`, cert-manager TLS. |
| `home-lan` | 8444 | Main home LAN (`192.168.1.0/24`) via the OPNsense WAN port forward 443 to 8444. Only Jellyfin is bound to it. |
| `cf-public` | 9443 | Plain HTTP from cloudflared; every public route. |
| `ssh` | 2222 | TCP passthrough to Forgejo SSH. |
| `metrics` | 9100 | Prometheus metrics (not exposed). |

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -3 | Argo CD Application for the `traefik` chart, with values from this repo. |
| `values.yaml` | - | DaemonSet, entrypoints above, dashboard IngressRoute behind auth, `allowCrossNamespace: false`, Prometheus metrics with entrypoint/router/service labels and a ServiceMonitor, resource limits. |
| `certificate.yaml` | 2 | Certificate for `traefik.internal.fferrando.cc`. |
| `middleware-dashboard-auth.yaml` | - | `basicAuth` middleware `traefik-dashboard-auth`. |
| `sealed-dashboard-auth.yaml` | - | SealedSecret `traefik-dashboard-auth-secret` (`users`, htpasswd). |
| `sealed-cloudflare-token.yaml` | -1 | SealedSecret `cloudflare-api-token-secret` (`token`) in the **`cert-manager`** namespace, used by the `letsencrypt-cloudflare` ClusterIssuer for DNS-01. |
