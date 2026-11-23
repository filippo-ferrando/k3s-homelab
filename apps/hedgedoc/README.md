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
| `permissions_patch.yaml` | 0 | ConfigMap `hedgedoc-permissions-patch`: patched `lib/permissions.js`, see [Local patch](#local-patch-hedgedoc-6946). |
| `pvc.yaml` | 0 | `hedgedoc-uploads` PVC (5Gi, default StorageClass) for uploaded images. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `hedgedoc`. |
| `deployment.yaml` | 5 | HedgeDoc 1.12.2 (`Recreate`, non-root uid 10000, `fsGroup: 10000`, all capabilities dropped), configured via `CMD_*` env vars, `lib/permissions.js` replaced by the patch ConfigMap, with readiness and liveness probes on `/_health`. Read-only root filesystem, `/tmp` is an emptyDir. |
| `service.yaml` | 5 | ClusterIP on 3000. |
| `ingressroute.yaml` | 5, 6 | `hedgedoc-headers` middleware (forces `X-Forwarded-Proto: https`, because TLS ends at Cloudflare and HedgeDoc would otherwise build `http://` URLs), the public IngressRoute and `public-ratelimit`. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace and CNPG on 5432 only. |

## Local patch (hedgedoc#6946)

HedgeDoc 1.12.2 moved the note view check into a shared `checkViewPermission()` (`lib/permissions.js`) that only understands the realtime request shape. On HTTP requests `req.user` has no `logged_in` field and the note owner is in `note.ownerId`, not `note.owner`. Every `GET /<note>` for a `private`, `limited` or `protected` note returns 403, the owner included. Upstream issue: [hedgedoc/hedgedoc#6946](https://github.com/hedgedoc/hedgedoc/issues/6946).

`permissions_patch.yaml` ships a corrected `permissions.js`, mounted with `subPath` over `/hedgedoc/lib/permissions.js`:

- Logged-in state: `user.logged_in` when it is a boolean (realtime, anonymous sockets carry `{ logged_in: false }`), otherwise `req.isAuthenticated()` (HTTP).
- Owner: `note.ownerId` (Sequelize note), otherwise `note.owner` (realtime UUID or included User).

Rolling back to 1.12.0 was not chosen: it lacks the 1.12.1 security fixes, and the database already contains the 1.12.1/1.12.2 migrations (`add-profile-provider`, `user-email-unique`).

**On the next HedgeDoc bump:** check whether the release fixes #6946. If it does, delete `permissions_patch.yaml` and the `permissions-patch` volume and volumeMount in `deployment.yaml`. The `subPath` mount would otherwise keep overriding the upstream file.
