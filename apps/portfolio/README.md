# portfolio

Personal website served at the apex domain. The image is built from its own repository and pushed to the Forgejo registry. Renovate bumps the date-based tag.

- **Namespace:** `portfolio` (PSS enforce `baseline`, warn `restricted`)
- **URL:** `https://fferrando.cc` (Cloudflare tunnel only)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `deployment.yaml` | 5 | Single replica of `git.fferrando.cc/rdfilippo/portfolio:<date-tag>`, `imagePullPolicy: Always`. |
| `service.yaml` | 5 | ClusterIP on 80. |
| `ingressroute.yaml` | 6 | Public route for `fferrando.cc` + `public-ratelimit` (60/min per `Cf-Connecting-Ip`). |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS and own namespace only. |

The homepage embeds the public Grafana dashboard from `status.fferrando.cc` (see `infrastructure/kube-prometheus-stack/dashboard-portfolio-public.yaml`).
