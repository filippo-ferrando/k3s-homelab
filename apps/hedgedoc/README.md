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
| `deployment.yaml` | 5 | HedgeDoc 1.12.0 (`Recreate`, non-root uid 10000, `fsGroup: 10000`, all capabilities dropped), configured via `CMD_*` env vars, with readiness and liveness probes on `/_health`. Read-only root filesystem, `/tmp` is an emptyDir. |
| `service.yaml` | 5 | ClusterIP on 3000. |
| `ingressroute.yaml` | 5, 6 | `hedgedoc-headers` middleware (forces `X-Forwarded-Proto: https`, because TLS ends at Cloudflare and HedgeDoc would otherwise build `http://` URLs), the public IngressRoute and `public-ratelimit`. |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace and CNPG on 5432 only. |

## Version pin (1.12.0)

Upstream removed the `1.12.1` and `1.12.2` tags from `quay.io/hedgedoc/hedgedoc`. `1.12.0` is the newest 1.12 tag available, so the deployment is pinned to it.

### hedgedoc#6946 does not apply

1.12.2 moved the note view check into a shared `checkViewPermission()` in `lib/permissions.js` that only understands the realtime request shape, so every HTTP `GET /<note>` for a `private`, `limited` or `protected` note returned 403 ([hedgedoc/hedgedoc#6946](https://github.com/hedgedoc/hedgedoc/issues/6946)). A ConfigMap mounted over that file worked around it.

1.12.0 has no `lib/permissions.js`. It keeps two separate checks, each correct for its caller:

- HTTP, `lib/web/note/util.js`: `req.isAuthenticated()` and `note.ownerId`.
- Realtime, `lib/realtime.js`: `req.user.logged_in` and `note.owner`.

The patch ConfigMap and its volume were removed. If a later release reintroduces `lib/permissions.js`, check whether #6946 is fixed before upgrading.

### Database schema

The `hedgedoc` database was migrated by 1.12.2 and contains two migrations that 1.12.0 does not ship: `20260922038700-add-profile-provider` and `20261001120000-user-email-unique`. 1.12.0 runs against this schema:

- Umzug only runs pending migrations. Extra rows in `SequelizeMeta` are ignored.
- `Users.profileProvider` is nullable. 1.12.0 does not write it, so new rows get `NULL`.
- The unique index on `(profileid, profileProvider)` cannot collide on `NULL` providers, and the unique index on `email` only matters for email registration, which is disabled.

### Security

1.12.0 lacks the fixes shipped in 1.12.1. Move back to a 1.12.x or later tag as soon as upstream publishes one.
