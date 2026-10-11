# notes

Runbooks and reference material for the homelab.

| Path | What it is |
|---|---|
| [`kubectl.md`](kubectl.md) | **The wiki.** Every cluster command: access, inspection, logs, secrets and sealing (with the full secret inventory), Argo CD, CNPG dump/restore, Longhorn, certificates, network policies, cleanup. |
| [`guides/bootstrap.md`](guides/bootstrap.md) | Step-by-step build of a new cluster, from Ansible to a converged GitOps state, plus the endpoint matrix. |
| [`guides/app_config.md`](guides/app_config.md) | How to manage app config the GitOps way: env vars vs. a mounted ConfigMap. |
| [`guides/jellyfin_home_lan.md`](guides/jellyfin_home_lan.md) | Exposing Jellyfin to the main home LAN (OPNsense port forward + dedicated Traefik entrypoint). |
| [`security/`](security/) | Security audits and their open findings. |

Conventions: kubectl and kubeseal commands go in `kubectl.md` only. Guides link to its sections instead of copying them.
