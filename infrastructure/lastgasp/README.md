# lastgasp

Node kernel-log collector, deployed from its own Helm chart on the Forgejo OCI registry. An agent on every node reads `/dev/kmsg` and ships the messages over UDP to a central server, which stores them in Postgres. This preserves the last kernel messages before a node hangs or crashes.

- **Namespace:** `lastgasp`
- **URL:** `https://lastgasp.internal.fferrando.cc` (LAN only, `/metrics` not routed)
- **Database:** `lastgasp` on `homelab-db`

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `repository.yaml` | - | Argo CD repository Secret `repo-forgejo-oci` for the Forgejo OCI Helm registry (public, no credentials). **Also used by `apps/kubecraft`.** |
| `db_secret_database.yaml` | - | SealedSecret `lastgasp-db-credentials` in `database`, used by the CNPG role. |
| `db_secret_lastgasp.yaml` | - | The same credentials sealed for `lastgasp`, used by the server. |
| `auth_secret.yaml` | - | SealedSecret `lastgasp-auth` (`auth`): UI authentication. |
| `join_secret.yaml` | - | SealedSecret `lastgasp-join` (`token`): the enrollment token agents use to join the server. |
| `certificate.yaml` | 2 | Certificate for `lastgasp.internal.fferrando.cc`. |
| `db.yaml` | 3, 4 | CNPG `DatabaseRole` + `Database` `lastgasp`. |
| `application.yaml` | 5 | Argo CD Application: chart `lastgasp` from `git.fferrando.cc/rdfilippo`, with values from this repo. |
| `values.yaml` | - | Server: public URL, Postgres (`sslmode=require`), auth via the proxy header with trusted pod CIDR, forward secrecy required. Agent: not privileged (all caps dropped except `SYSLOG`, `IPC_LOCK`, `SYS_RESOURCE`), read-only rootfs, SELinux `spc_t`, gets `/dev/kmsg` through the `devic.es/kmsg` resource. ServiceMonitor and PrometheusRule enabled. |
| `ingressroute.yaml` | 6 | Internal route to `lastgasp-http:8080`, excluding `/metrics`. |
| `networkpolicy.yaml` | - | Server: UDP 5140 from agents only, TCP 8080 from Traefik and Prometheus; egress to DNS and CNPG. Agents: no ingress; egress to DNS and the server's UDP 5140 only. |

**Prerequisites:** `infrastructure/generic-device-plugin` (provides `devic.es/kmsg`), and a 5432 allow entry for `app.kubernetes.io/component: server` in `apps/database/networkpolicy.yaml`.
