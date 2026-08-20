## generate the sealed secrets

1. gather working kubeconfig file

```bash
kubectl create secret generic cloudflare-api-token-secret \
  --namespace cert-manager \
  --from-literal=api-token="YOUR_REAL_API_TOKEN_HERE" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > sealed-cloudflare-token.yaml
```

```bash
kubectl create secret generic tunnel-token \
  --namespace cloudflared \
  --from-literal=token="YOUR_REAL_TUNNEL_TOKEN_HERE" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > sealed-tunnel-token.yaml
```
