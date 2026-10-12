# pushgateway

Prometheus Pushgateway. It receives metrics pushed by the Borg backup jobs that run on the hosts (`ansible/provision/07_backups.yml`), so backup status shows up in Prometheus and Grafana.

- **Namespace:** `monitoring`
- **URL:** `https://pushgateway.internal.fferrando.cc` (LAN only, where the backup scripts push)
- **Persistence:** pushed metrics are written to a PVC, so they survive pod restarts (node reboots, Kured, rollouts). Without it, the backup metrics disappear on every restart until the next backup run (every 2 days).

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | 1 | Argo CD Application for the `prometheus-pushgateway` chart, with values from this repo. |
| `values.yaml` | - | ServiceMonitor in `monitoring`, memory limits, persistence (100Mi `longhorn-single-replica` PVC, flushed every minute to `/data/pushgateway.data`). |
| `certificate.yaml` | 2 | Certificate for `pushgateway.internal.fferrando.cc`. |
| `ingressroute.yaml` | 2 | Internal route to `pushgateway-prometheus-pushgateway:9091`. |
