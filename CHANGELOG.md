# Changelog

Major changes to the homelab only: new deployments, removed services and architecture-level decisions.
Small fixes, typos and Renovate version bumps are left out; `git log` has those.
Newest first.

---

## 2026-10-11: Argo CD manages itself

**What**
- Added the `argocd` Application (`infrastructure/argocd/application.yaml`, wave -5) for the `argo-cd` Helm chart `10.9.0` (Argo CD `v3.5.2`, the version already running), with `infrastructure/argocd/values.yaml`.
- Moved `server.insecure` from the hand-written `argocd-cmd-params-cm` in `argocd-ingress.yaml` into the chart values.
- `ansible/02_bootstrap_cluster.yml` now renders the same chart, version and values with `helm template` instead of applying the floating `stable` manifest.
- Prune is disabled and there is no resources finalizer, so Argo CD can't delete itself.
- One-time migration: the chart's pod selectors differ from the upstream manifests' (and are immutable), so the old Deployments/StatefulSet were deleted with `--cascade=orphan` before the first sync.

**Why**
- Argo CD was installed once from the floating `stable` manifest and never upgraded or tracked in Git.
- The Helm chart matches how every other infrastructure component is deployed (Application + `values.yaml`) and lets Renovate track it.

## 2026-10-10: Security hardening pass

**What**
- Added **egress** NetworkPolicies to every app namespace and to `cloudflared`. Each namespace can now reach only DNS, its own pods, the CNPG cluster on 5432 (if it uses the DB) and, where needed, the public internet. Private ranges (LAN/NAS, nodes, pod/service CIDRs, tailnet) are excluded.
- Made `apps/database/networkpolicy.yaml` stricter. Port 5432 now accepts only the specific pods that hold DB credentials (matched by namespace and pod label), not whole namespaces. For kubecraft this is the manager only, because game servers run user code.
- Disabled Traefik cross-namespace references (`allowCrossNamespace: false`). The shared rate-limit middleware in the `traefik` namespace was removed, and each app now defines its own `public-ratelimit` middleware.
- Set resource requests and limits on every pod, including Helm-managed ones (cert-manager, CNPG operator, Falco, kube-prometheus-stack, kured, pushgateway, sealed-secrets, Traefik).
- Set `primaryUpdateMethod: switchover` on the CNPG cluster.
- Lastgasp agents no longer run privileged. `/dev/kmsg` is now handed to them as a device resource by the new `generic-device-plugin` DaemonSet.

**Why**
- A security audit found that a compromised pod could reach anything on the LAN or in the cluster. Egress rules limit the blast radius.
- Cross-namespace middlewares let any namespace attach to another namespace's objects.
- Pods without limits could starve nodes.
- During a rolling update, CNPG restarted the primary in place and blocked writes for about 3 minutes. Switchover promotes a replica first.

## 2026-10-09: kubecraft (Minecraft server manager)

**What**
- Deployed kubecraft from its own Helm chart, published on the Forgejo OCI registry, into the `minecraft` namespace. It has a CNPG database, a public management UI at `mine.fferrando.cc` (with a rate limit on the login path), mc-router as a LoadBalancer with scale-to-zero after 15 minutes, and Prometheus metrics with a Grafana dashboard.
- Added a playit.gg tunnel for player traffic.

**Why**
- To self-host on-demand Minecraft servers.
- playit is needed because the Cloudflare tunnel cannot carry raw TCP game traffic.

## 2026-10-08: Public Grafana dashboards

**What**
- Anonymized copies of the homelab overview dashboard and a portfolio dashboard are now exposed through Grafana "Shared dashboards" at `status.fferrando.cc`.
- Only the public-dashboard paths are routed. They have their own rate limit, and their CSP allows embedding only from `fferrando.cc`.
- The internal Grafana UI now sends `X-Frame-Options: DENY`.

**Why**
- To show live cluster stats on the portfolio homepage without exposing the Grafana login or the query API.
- Every query aggregates away node, IP, pod and namespace labels, because the public API returns full series labels.

## 2026-10-08: lastgasp (node kernel-log collector)

**What**
- Deployed lastgasp from its own Helm chart on the Forgejo OCI registry.
- Agents on every node read `/dev/kmsg` and send it over UDP to a server that stores it in CNPG. The internal UI is at `lastgasp.internal.fferrando.cc`. Metrics, PrometheusRules and a row in the overview dashboard were added.
- Registered the Forgejo OCI Helm repository in Argo CD (`infrastructure/lastgasp/repository.yaml`).

**Why**
- To keep the kernel messages a node emits right before it hangs or crashes, which are otherwise lost on reboot.

## 2026-09-23: Network policies, Falco IDS, dashboard auth

**What**
- Added ingress NetworkPolicies to every namespace: only the namespace itself and Traefik can reach app pods, and the database accepts only its clients and Prometheus.
- Deployed **Falco** with the modern eBPF driver and Falcosidekick, with metrics in Prometheus. Custom rules whitelist known-good behaviour: CNPG WAL archiving, controllers that talk to the k8s API, Forgejo sshd and binary updates.
- Put the Traefik dashboard behind basic auth (sealed secret).

**Why**
- Until this point any pod could talk to any other pod.
- Falco adds runtime intrusion detection. The exceptions keep its alerts actionable instead of noisy.

## 2026-09-11: Forgejo outgoing mail

**What:** Configured the Forgejo mailer to use Resend SMTP. The credentials are in a sealed secret.
**Why:** For registration, notification and password-reset emails.

## 2026-09-10: Documentation

**What:** Added the root `README.md` (architecture, stack, bootstrap) and moved notes into `notes/`.

## 2026-09-03: Descheduler, DB anti-affinity, pinned images

**What**
- Deployed the descheduler as a CronJob that runs every 2 hours.
- Changed CNPG pod anti-affinity to `required`.
- Pinned every container image to an explicit tag.
- Renamed the Ansible maintenance playbooks to `patch_cluster.yml` and `prune_cached_images.yml`.

**Why**
- After kured reboots, pods piled up on the nodes that stayed up. The descheduler rebalances them.
- Two DB replicas must never share a node, even during a reboot. A pending replica is acceptable.
- Pinned tags let Renovate open version-bump PRs.

## 2026-09-01: Dashboards as code, vibravid

**What**
- Added Grafana dashboards as ConfigMaps that the Grafana sidecar loads.
- Enabled metrics for CNPG (PodMonitor) and cert-manager.
- Deployed **vibravid**, a video downloader that writes into the media NFS share.

**Why**
- Dashboards in Git survive Grafana restarts.
- Files that vibravid downloads appear directly in Jellyfin.

## 2026-08-31: Renovate, kured, LibrePhotos

**What**
- Added Renovate (`renovate.json`) for automated dependency PRs on images and Helm charts. Codeberg sources are polled through a mirror to get around Codeberg's anti-bot policy.
- Added the `patch_cluster` Ansible playbook for OS updates and **kured**, which drains and reboots nodes one at a time, every day between 01:00 and 05:00. The drain settings are tuned for Longhorn volume handoff and CNPG failover.
- Deployed **LibrePhotos** (backend, frontend, proxy, redis) over the NFS photo folders. It replaced **Lychee**, which was tried the same day and removed after permission and import problems.

**Why**
- To keep images, charts and the OS patched without manual work.
- To have a self-hosted photo library.

## 2026-08-30: Automated DB provisioning, FileBrowser Quantum, failed experiments

**What**
- Per-app databases are now declared in Git as CNPG `DatabaseRole` + `Database` resources. The password comes from a SealedSecret in the `database` namespace, and a copy goes to the app namespace. Hedgedoc, Vaultwarden, Jellyfin and Forgejo were migrated to this pattern.
- Deployed **FileBrowser Quantum** as a web file manager over the NFS media and data shares.
- Tried and removed **Seafile**, **Baïkal** and **vdirsyncer** (calendar sync).

**Why**
- Creating roles and databases by hand with `psql` was not GitOps.
- Seafile and Baïkal/vdirsyncer did not fit well enough to keep.

## 2026-08-29: Hedgedoc, Vaultwarden, Jellyfin

**What**
- Deployed **Hedgedoc**: public at `doc.fferrando.cc` with registration disabled.
- Deployed **Vaultwarden**: internal only, signups disabled.
- Deployed **Jellyfin** with the PostgreSQL-backed image, media mounted read-only from NFS.

**Why:** To self-host notes, passwords and media streaming on the shared HA Postgres.

## 2026-08-28: GitOps reconciliation working, first apps

**What**
- Got the Argo CD app-of-apps working end to end. `system/root-app.yaml` creates `root-infrastructure` (wave -1) and `root-apps` (wave 1), and sync waves order the CRDs, secrets, certs and workloads.
- Moved the Cloudflare and tunnel tokens into Sealed Secrets.
- Added Prometheus metrics for Traefik and Longhorn.
- Deployed **Forgejo**: data on NFS, SSH through the Traefik `ssh` entrypoint.
- Deployed **portfolio** at `fferrando.cc`.
- Cloudflared now forwards to Traefik's `cf-public` entrypoint over plain HTTP, because TLS terminates at Cloudflare.

**Why:** To have a fully declarative cluster with no hand-applied manifests.

## 2026-08-21: Monitoring stack

**What:** Deployed kube-prometheus-stack (Prometheus, Grafana, Alertmanager) and Pushgateway, with internal IngressRoutes.
**Why:** For cluster observability. The Pushgateway receives metrics from the Borg backup jobs that Ansible runs on the hosts.

## 2026-08-20: Initial cluster

**What**
- Ansible playbooks for OS prep, the k3s HA bootstrap (embedded etcd, 3 servers + 1 agent), Borg backups and NFS shares.
- Core infrastructure: Argo CD, Traefik (DaemonSet), cert-manager with Let's Encrypt DNS-01 via Cloudflare, Sealed Secrets and cloudflared.
- **Longhorn** for block storage, with 3 replicas by default.
- **CloudNativePG**: a 3-instance HA Postgres cluster (`homelab-db`).
- The DB runs on a `longhorn-single-replica` StorageClass.

**Why**
- To have the whole homelab as code from day one.
- CNPG already replicates at the Postgres level, so 3 Longhorn replicas under each of 3 DB instances would mean 9 copies of the data and wasted I/O.
