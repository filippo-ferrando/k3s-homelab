# argocd

Argo CD manages **itself** through the [`argo-cd` Helm chart](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd). `ansible/02_bootstrap_cluster.yml` installs the same chart, version and values once on a new cluster. From then on, the `argocd` Application below keeps it in sync with Git, and Renovate bumps the chart version.

- **Namespace:** `argocd`
- **URL:** `https://argocd.internal.fferrando.cc` (LAN only)

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -5 | Argo CD Application `argocd` for the `argo-cd` chart, with values from this repo. Uses `ServerSideApply` (the ApplicationSet CRD is too large for client-side apply) and `selfHeal`. **No prune** and **no resources finalizer**, so neither a broken render nor deleting this Application can remove Argo CD or its CRDs. |
| `values.yaml` | - | `configs.cm.url` and `server.insecure: true` (TLS terminates at Traefik, so argocd-server serves plain HTTP). |
| `argocd-ingress.yaml` | 2 | IngressRoute on `websecure` for the UI. |
| `certificate.yaml` | 2 | cert-manager Certificate `argocd-internal-tls`. |
| `networkpolicy.yaml` | 2 | Ingress only from the `argocd` namespace and Traefik. The chart adds its own per-component NetworkPolicies on top. |

## Upgrading

Merge the Renovate PR for the chart. Read the chart and Argo CD upgrade notes first for major versions. Because prune is off, resources the chart stops rendering stay in the cluster: Argo CD shows them as orphaned, and you delete them by hand.
