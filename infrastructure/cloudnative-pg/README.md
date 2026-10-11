# cloudnative-pg

[CloudNativePG](https://cloudnative-pg.io) operator. It manages the `homelab-db` Postgres cluster (`apps/database`) and the per-app `DatabaseRole`/`Database` resources.

- **Namespace:** `cnpg-system`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -3 | Argo CD Application for the `cloudnative-pg` chart, with memory limits. Uses `ServerSideApply=true` because the CRDs are too large for client-side apply annotations. |
