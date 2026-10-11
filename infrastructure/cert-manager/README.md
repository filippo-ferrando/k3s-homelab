# cert-manager

[cert-manager](https://cert-manager.io) issues every `*.internal.fferrando.cc` certificate from Let's Encrypt using Cloudflare DNS-01. This works for LAN-only hostnames because no inbound HTTP challenge is needed. Public hostnames get TLS from Cloudflare instead.

- **Namespace:** `cert-manager`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -3 | Argo CD Application for the `jetstack/cert-manager` chart: installs CRDs, enables a ServiceMonitor for kube-prometheus-stack, and sets memory limits for controller, cainjector and webhook. |
| `cluster-issuer.yaml` | 1 | `ClusterIssuer` `letsencrypt-cloudflare` (ACME production, DNS-01 via Cloudflare). Every `Certificate` in the repo references it. |

**Prerequisite:** the Cloudflare API token secret `cloudflare-api-token-secret` (key `token`) in `cert-manager`. It lives in `infrastructure/traefik/sealed-cloudflare-token.yaml`.
