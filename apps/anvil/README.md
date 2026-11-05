# anvil

Project website for [anvil](https://git.fferrando.cc/anvil/anvil) (VMs and containers, one CLI). The site is a fully prerendered SvelteKit build served by `nginxinc/nginx-unprivileged`. The image is built from the `anvil/website` repository by its `publish.yml` workflow (multi-stage Dockerfile, `linux/amd64`) and pushed to the Forgejo registry on every push to `main`. Renovate bumps the date-based tag.

- **Namespace:** `anvil-website` (PSS `restricted`)
- **URL:** `https://anvil.fferrando.cc` (Cloudflare tunnel only)
- **Image:** `git.fferrando.cc/anvil/website:<YYYYMMDD-HHMM>` (public package, no pull secret)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `deployment.yaml` | 5 | Single replica of `git.fferrando.cc/anvil/website:<date-tag>`, `imagePullPolicy: Always`. Non-root (uid 101), all capabilities dropped, read-only root filesystem, service account token not mounted; nginx writes its pid and temp files to an emptyDir on `/tmp`. Listens on 8080. Readiness (every 10s) and liveness (every 30s, 3 failures) probes on `/healthz`. |
| `service.yaml` | 5 | ClusterIP on 80, targets the container's `http` port (8080). |
| `ingressroute.yaml` | 6 | Public route for `anvil.fferrando.cc` + `public-ratelimit` (60/min, burst 30, per `Cf-Connecting-Ip`). |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS and own namespace only (static site, no internet). |

## Notes

- The CI workflow pushes to `git.internal.fferrando.cc/anvil/website`; the manifest pulls the same package through `git.fferrando.cc`. Both hostnames serve the same Forgejo registry.
- The image exposes `/healthz` (returns `ok`, access log disabled) on 8080. The Kubernetes readiness and liveness probes and the image's Docker `HEALTHCHECK` all use it. `apps/portfolio` uses the same probe timings on `/`, since its image has no `/healthz`.
- The public hostname `anvil.fferrando.cc` is mapped to Traefik's `cf-public` entrypoint in the Cloudflare Zero Trust dashboard (see `infrastructure/cloudflared/README.md`).
