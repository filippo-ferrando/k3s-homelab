# keda

[KEDA](https://keda.sh) event-driven autoscaler. Used by `apps/forgejo-runner`: a `ScaledJob` with the `forgejo-runner` scaler starts one runner Job per pending Forgejo Actions job.

- **Namespace:** `keda`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -2 | Argo CD Application for the `kedacore/keda` chart, with values from this repo. Wave -2 so the `ScaledJob`/`TriggerAuthentication` CRDs exist before `root-apps`. `ServerSideApply=true` for the large CRDs. |
| `values.yaml` | - | Operator Prometheus metrics with a ServiceMonitor (`keda_scaler_metrics_value`, `keda_scaler_errors_total`), read by the "Forgejo CI Runners" dashboard row. Resource requests and memory limits for the operator, metrics apiserver and admission webhooks. |

The chart ships no NetworkPolicy. The operator reaches Forgejo through the `keda` ingress entry in `apps/forgejo/networkpolicy.yaml`.

The scaler metrics are scraped from the `keda` namespace, so the `namespace` label of the scaled resource is renamed to `exported_namespace`. Dashboard queries filter on `scaledObject` instead.
