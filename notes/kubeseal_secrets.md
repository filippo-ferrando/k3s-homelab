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
  --format yaml > infrastructure/traefik/sealed-cloudflare-token.yaml
```

```bash
kubectl create secret generic tunnel-token \
  --namespace cloudflared \
  --from-literal=token="YOUR_REAL_TUNNEL_TOKEN_HERE" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/cloudflared/sealed-tunnel-token.yaml
```

## longhorn auth middlewate secret creation

```bash
htpasswd -nb admin "YourStrongPasswordHere"
```

```bash
kubectl create secret generic longhorn-auth-secret \
  --namespace longhorn-system \
  --from-literal=users="admin:\$apr1\$mK3...\$v8xQ5a6gS8xL.1" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/manifests/sealed-longhorn-auth.yaml
```

## traefik dashboard basicauth secret creation

```bash
HTPASSWD_HASH=$(htpasswd -nb admin "YourStrongPasswordHere")

kubectl create secret generic traefik-dashboard-auth-secret \
  --namespace traefik \
  --from-literal=users="${HTPASSWD_HASH}" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/traefik/sealed-dashboard-auth.yaml
```

forgejo db password secret creation

```bash
kubectl -n forgejo create secret generic forgejo-db \
        --from-literal=password="$(kubectl -n database get secret homelab-db-app -o jsonpath='{.data.password}' | base64 -d)"
```

## lastgasp secrets

All four end up in `infrastructure/lastgasp/`. Argo CD keeps the `lastgasp` app degraded until they are pushed.

1. db credentials: same password in `database` (for the CNPG `DatabaseRole`) and in `lastgasp` (for the server).
   The username must be `lastgasp`, the role name in `infrastructure/lastgasp/db.yaml`.

```bash
DB_PW="$(openssl rand -base64 32 | tr -d '/+=')"

for ns in database lastgasp; do
  kubectl create secret generic lastgasp-db-credentials \
    --namespace "$ns" \
    --from-literal=username=lastgasp \
    --from-literal=password="$DB_PW" \
    --dry-run=client -o yaml | \
  kubectl label --local -f - cnpg.io/reload=true -o yaml | \
  kubeseal \
    --controller-namespace kube-system \
    --controller-name sealed-secrets \
    --format yaml > "infrastructure/lastgasp/db_secret_${ns}.yaml"
done
```

2. shared agent key (64 hex chars). Pre-made because the chart's random key uses `lookup`, which Argo CD can't run.

```bash
KEY="$(openssl rand -hex 32)"

kubectl create secret generic lastgasp-key \
  --namespace lastgasp \
  --from-literal=agent.key="$KEY" \
  --from-literal=keys="*  $KEY" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/lastgasp/key_secret.yaml
```

3. web UI login: an auth file with one `name role hash` line per user (roles: `admin`, `viewer`).
   `user` reads the password from stdin, `token` prints a new API token and its line.

```bash
IMG=git.fferrando.cc/rdfilippo/lastgasp-server:latest

docker run --rm -it "$IMG" user admin admin > auth   # asks for the password
# more lines, e.g. a read-only API token:
# docker run --rm "$IMG" token grafana viewer >> auth

kubectl create secret generic lastgasp-auth \
  --namespace lastgasp \
  --from-file=auth=auth \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/lastgasp/auth_secret.yaml

shred -u auth
```

## kubecraft secrets

All three end up in `apps/kubecraft/`. The app stays degraded until they are pushed.

1. db credentials: same password in `database` (for the CNPG `DatabaseRole`) and in `minecraft` (for the manager).
   The username must be `kubecraft`, the role name in `apps/kubecraft/db.yaml`.

```bash
DB_PW="$(openssl rand -base64 32 | tr -d '/+=')"

kubectl create secret generic kubecraft-db-credentials \
  --namespace database \
  --from-literal=username=kubecraft \
  --from-literal=password="$DB_PW" \
  --dry-run=client -o yaml | \
kubectl label --local -f - cnpg.io/reload=true -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > apps/kubecraft/db_secret.yaml

kubectl create secret generic kubecraft-db-credentials \
  --namespace minecraft \
  --from-literal=username=kubecraft \
  --from-literal=password="$DB_PW" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > apps/kubecraft/deployment_secret.yaml
```

2. session secret and the first admin. The admin must change the password at first login.

```bash
ADMIN_PW="$(openssl rand -base64 18)"
echo "kubecraft bootstrap admin password: $ADMIN_PW"

kubectl create secret generic kubecraft-secrets \
  --namespace minecraft \
  --from-literal=SESSION_SECRET="$(openssl rand -hex 32)" \
  --from-literal=BOOTSTRAP_ADMIN_USER=admin \
  --from-literal=BOOTSTRAP_ADMIN_PASSWORD="$ADMIN_PW" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > apps/kubecraft/secrets.yaml
```
