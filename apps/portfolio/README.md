# portfolio

Personal website served at the apex domain. The image (`nginxinc/nginx-unprivileged` plus the Astro `dist/`, see `docker/` in the portfolio repo) is built from its own repository and pushed to the Forgejo registry. Renovate bumps the date-based tag.

- **Namespace:** `portfolio` (PSS `restricted`)
- **URL:** `https://fferrando.cc` (Cloudflare tunnel only)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `deployment.yaml` | 5 | Single replica of `git.fferrando.cc/rdfilippo/portfolio:<date-tag>`, `imagePullPolicy: Always`. Non-root (uid 101), all capabilities dropped, read-only root filesystem; nginx writes its pid and temp files to an emptyDir on `/tmp`. Listens on 8080. |
| `service.yaml` | 5 | ClusterIP on 80, targets the container's `http` port (8080). |
| `ingressroute.yaml` | 6 | Public route for `fferrando.cc` + `public-ratelimit` (60/min per `Cf-Connecting-Ip`). |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS and own namespace only. |

The homepage embeds the public Grafana dashboard from `status.fferrando.cc` (see `infrastructure/kube-prometheus-stack/dashboard-portfolio-public.yaml`).
