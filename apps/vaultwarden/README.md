# vaultwarden

[Vaultwarden](https://github.com/dani-garcia/vaultwarden): Bitwarden-compatible password manager. **LAN only** (no public route). Signups are disabled; new users join by invitation.

- **Namespace:** `vaultwarden` (PSS enforce `baseline`, warn `restricted`)
- **URL:** `https://vault.internal.fferrando.cc`
- **Database:** `vaultwarden` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `db_secret.yaml` | 0 | SealedSecret `vaultwarden-db-credentials` in `database`, used by the CNPG role. |
| `deployment_secret.yaml` | 0 | The same credentials sealed for `vaultwarden`. |
| `pvc.yaml` | 0 | `vaultwarden-data` PVC (3Gi, `longhorn`, RWO) for `/data` (attachments, icons, keys). |
| `certificate.yaml` | 2 | cert-manager Certificate for `vault.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `vaultwarden`. |
| `deployment.yaml` | 5 | Vaultwarden (alpine image, `Recreate`). `DATABASE_URL` is built from the secret's username and password, websockets are enabled, probes on `/alive`. |
| `service.yaml` | 5 | ClusterIP on 80. |
| `ingressroute.yaml` | 6 | Internal route only (`websecure` + TLS). |
| `networkpolicy.yaml` | - | Ingress from own namespace + Traefik. Egress to DNS, own namespace, CNPG and the public internet (icon fetching). |
