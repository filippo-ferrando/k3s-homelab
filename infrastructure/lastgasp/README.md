# lastgasp

Node kernel-log collector, deployed from its own Helm chart (`0.2.0`, app `v0.2.0`) on the Forgejo OCI registry. An agent on every node reads `/dev/kmsg`, pstore crash logs and the node journal (`warning` and more severe) and ships them over UDP to a central server, which stores them in Postgres. This preserves the last messages before a node hangs or crashes.

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
| `application.yaml` | 5 | Argo CD Application: chart `lastgasp` `0.2.0` from `git.fferrando.cc/rdfilippo`, with values from this repo. |
| `values.yaml` | - | Server: public URL, Postgres (`sslmode=require`), retention 720h or 2GiB (`retainBytes`), auth via the proxy header with trusted pod CIDR, forward secrecy required. Agent: not privileged (all caps dropped except `SYSLOG`, `IPC_LOCK`, `SYS_RESOURCE`), read-only rootfs, SELinux `spc_t`, gets `/dev/kmsg` through the `devic.es/kmsg` resource. Journal shipping enabled (`lastgasp-agent-journal` image, priority `warning`, 200 lines/s, `persistent: false`), memory limit 192Mi. ServiceMonitor and PrometheusRule enabled. |
| `ingressroute.yaml` | 6 | Internal route to `lastgasp-http:8080`, excluding `/metrics`. |
| `networkpolicy.yaml` | - | Server: UDP 5140 from agents only, TCP 8080 from Traefik and Prometheus; egress to DNS and CNPG. Agents: no ingress; egress to DNS and the server's UDP 5140 only. |

**Prerequisites:** `infrastructure/generic-device-plugin` (provides `devic.es/kmsg`), and a 5432 allow entry for `app.kubernetes.io/component: server` in `apps/database/networkpolicy.yaml`.

## Chart options

| Option | State | Notes |
|---|---|---|
| `agent.journal` | Enabled | The nodes keep the journal in RAM only (`/run/log/journal`, no `/var/log/journal`), so `persistent: false`. With `persistent: true` the pod does not start on these nodes. The journal image ships journalctl from systemd 257, the same version as AlmaLinux 10. |
| `agent.pstore` | Enabled (default) | Since `0.2.0` the agent also mounts `/var/lib/systemd/pstore` read-only, where systemd-pstore moves crash files at boot. |
| `server.retainBytes` | `2GiB` | Caps the records on the shared `homelab-db`, together with the 720h time retention. |
| `server.incidents` | Chart defaults | Flapping after 3 reboots in 1h; hosts that reboot or go silent within 2m (3 or more) share one alert. |
| `agent.pmsg` | Disabled | The AlmaLinux kernel is built without `CONFIG_PSTORE_PMSG`, and the pod does not start without `/dev/pmsg0`. |
| `server.netconsole` | Disabled | Needs the server pinned to one node, a NodePort with `externalTrafficPolicy: Local`, a NetworkPolicy rule for UDP from `192.168.10.0/24` and `modprobe.d` config on every node. |
