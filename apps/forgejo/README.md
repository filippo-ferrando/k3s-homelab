# forgejo

[Forgejo](https://forgejo.org) Git forge. Besides hosting repositories, it serves as the container registry for the `portfolio` image and as the OCI Helm registry for the `kubecraft` and `lastgasp` charts.

- **Namespace:** `forgejo` (PSS enforce `baseline`, warn `restricted`)
- **URLs:** `https://git.internal.fferrando.cc` (LAN), `https://git.fferrando.cc` (Cloudflare tunnel, rate-limited), SSH on Traefik port `2222`
- **Database:** `forgejo` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `forgejo-db-credentials` (`username`, `password`) in the `database` namespace, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | The same credentials sealed for the `forgejo` namespace, read by the pod. |
| `resend-secrets.yaml` | - | SealedSecret `forgejo-resend-credentials` (`smtp-user`, `smtp-password`) for the Resend SMTP mailer. |
| `volume.yaml` | 0 | Static NFS PV + PVC `forgejo-data` pointing at `192.168.10.101:/mnt/vault/git`, mounted at `/data` (repos + app data). |
| `private-certficate.yaml` | 2 | cert-manager Certificate for `git.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` `forgejo` + `Database` `forgejo`. |
| `deployment.yaml` | 5 | Forgejo 16, configured entirely through `FORGEJO__*` env vars: Postgres, Resend SMTP mailer (`git@fferrando.cc`), Actions default URL `https://github.com`. |
| `service.yaml` | 5 | ClusterIP: `3000` (http) and `22` (ssh). |
| `ingressroute.yaml` | 6 | Internal route, public route with `public-ratelimit`, and an `IngressRouteTCP` on the Traefik `ssh` entrypoint for git over SSH. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace, CNPG on 5432 and the public internet (mirrors, Resend, Actions). |

**Prerequisites:** NFS export `/mnt/vault/git`, the `homelab-db` cluster, and a 5432 allow entry for `app: forgejo` in `apps/database/networkpolicy.yaml`.
