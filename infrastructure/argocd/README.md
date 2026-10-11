# argocd

Extra configuration for Argo CD itself. Argo CD is installed once by `ansible/02_bootstrap_cluster.yml`, then `system/root-app.yaml` points it at `infrastructure/` and `apps/` (app-of-apps). This folder only adds what Argo CD needs to be reachable.

- **Namespace:** `argocd`
- **URL:** `https://argocd.internal.fferrando.cc` (LAN only)

## Files

| File | Wave | Description |
|---|---|---|
| `argocd-ingress.yaml` | 0, 2 | `argocd-cmd-params-cm` with `server.insecure: "true"` (TLS terminates at Traefik, so argocd-server must serve plain HTTP to avoid a redirect loop), plus the IngressRoute on `websecure`. |
| `certificate.yaml` | 2 | cert-manager Certificate `argocd-internal-tls`. |
| `networkpolicy.yaml` | 2 | Ingress only from the `argocd` namespace and Traefik. |
