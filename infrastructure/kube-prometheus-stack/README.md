# kube-prometheus-stack

Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics and the Prometheus operator. Prometheus picks up every ServiceMonitor/PodMonitor in every namespace (no label selector).

- **Namespace:** `monitoring`
- **URLs:** `https://stats.internal.fferrando.cc` (Grafana, LAN), `https://status.fferrando.cc` (public shared dashboards only, Cloudflare tunnel)

## Files

| File | Wave | Description |
|---|---|---|
| `namespace.yaml` | -3 | Namespace. |
| `application.yaml` | -1 | Argo CD Application for the chart, with values from this repo. `ServerSideApply=true` for the large CRDs. |
| `values.yaml` | - | Prometheus retention 3d / 3GiB on 7Gi `longhorn-single-replica`, cluster-wide monitor selection, heavy apiserver/etcd histogram metrics dropped. node-exporter runs as root with SELinux type `spc_t` + `DAC_READ_SEARCH` so filesystem metrics work on `--selinux` k3s nodes. Grafana has persistence and `allow_embedding: true`. Resource limits for every component. |
| `certificate.yaml` | 2 | Certificate for `stats.internal.fferrando.cc`. |
| `ingressroute.yaml` | 2 | Internal Grafana route with the `grafana-ui-deny-frame` middleware. |
| `ingressroute-public.yaml` | 2 | Public route on `cf-public` that matches **only** `/public-dashboards/`, `/api/public/` and `/public/`. Login, `/d/*`, the datasource API and Explore never leave the LAN. |
| `middleware-grafana-embed-headers.yaml` | - | `grafana-public-embed` (CSP `frame-ancestors https://fferrando.cc`) and `grafana-ui-deny-frame` (`X-Frame-Options: DENY`). Framing is controlled per route here, because Grafana's own header is disabled. |
| `middleware-ratelimit-grafana-public.yaml` | - | 300/min (burst 150) per `Cf-Connecting-Ip`. A shared dashboard makes about 55 requests per load, too many for the standard 60/min limit. |
| `networkpolicy.yaml` | - | Ingress only from `monitoring` and Traefik. |
| `dashboard-homelab-overview.yaml` | - | Main dashboard (cluster, nodes, Longhorn, Traefik, CNPG, Borg, lastgasp), as a ConfigMap labelled `grafana_dashboard` for the sidecar. |
| `dashboard-homelab-public.yaml` | - | Anonymized copy of the overview for public sharing. Every query aggregates away node/IP/namespace/pod/PVC/DB labels. |
| `dashboard-portfolio-public.yaml` | - | Public, anonymized portfolio pod dashboard, embedded on the `fferrando.cc` homepage. |
| `dashboard-kubecraft.yaml` | - | kubecraft servers, players, resources, manager and mc-router metrics. |

Dashboards are GitOps-managed: edits made in the UI are lost on restart. Export the JSON and update the ConfigMap instead. The Grafana admin password must be changed on first login. See `notes/guides/app_config.md`.
