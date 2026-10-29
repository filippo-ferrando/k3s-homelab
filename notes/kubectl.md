# kubectl wiki

Every cluster command in one place, one or two examples per task. All commands are bash; run them from the repo root.
Placeholders: `<ns>` namespace, `<pod>` pod name, `<app>` app/folder name.

- [Access](#access)
- [Inspect resources](#inspect-resources)
- [Logs, exec, debug](#logs-exec-debug)
- [Port-forward](#port-forward)
- [Restart, scale, rollout](#restart-scale-rollout)
- [Nodes](#nodes)
- [Secrets](#secrets)
- [Sealed Secrets](#sealed-secrets)
- [Argo CD](#argo-cd)
- [Database (CNPG)](#database-cnpg)
- [Storage (Longhorn, PVCs)](#storage-longhorn-pvcs)
- [Certificates (cert-manager)](#certificates-cert-manager)
- [Networking and NetworkPolicies](#networking-and-networkpolicies)
- [Monitoring and Falco](#monitoring-and-falco)
- [Cleanup and stuck resources](#cleanup-and-stuck-resources)

---

## Access

Fetch the kubeconfig from the first server (`magi`) and point it at its LAN IP:

```bash
mkdir -p ~/.kube
scp magi@192.168.10.100:/etc/rancher/k3s/k3s.yaml ~/.kube/config
sed -i 's/127.0.0.1/192.168.10.100/g' ~/.kube/config
kubectl get nodes
```

Switch the default namespace for the current context:

```bash
kubectl config set-context --current --namespace=database
kubectl config get-contexts
```

## Inspect resources

```bash
kubectl get pods -A -o wide                     # every pod, with node and IP
kubectl get pods -n <ns> -l app=<app>           # filter by label
kubectl get all,pvc,ingressroute -n <ns>        # most of an app's objects at once
```

```bash
kubectl describe pod <pod> -n <ns>              # events, probes, mounts, scheduling errors
kubectl get deploy <app> -n <ns> -o yaml        # full live object
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].image}'
```

Events (the first place to look when something is Pending or CrashLooping):

```bash
kubectl get events -n <ns> --sort-by=.lastTimestamp
kubectl get events -A --field-selector type=Warning
```

Resource usage (metrics-server ships with k3s):

```bash
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -20
```

## Logs, exec, debug

```bash
kubectl logs -n <ns> deploy/<app> -f --tail=100   # follow, picks one pod of the deployment
kubectl logs -n <ns> <pod> --previous             # logs of the last crashed container
kubectl logs -n <ns> -l app=<app> --all-containers --prefix
```

```bash
kubectl exec -it -n <ns> deploy/<app> -- sh
kubectl exec -n <ns> <pod> -c <container> -- env  # one-shot command in a specific container
```

Ephemeral debug container (for distroless images with no shell, e.g. cloudflared):

```bash
kubectl debug -it -n cloudflared deploy/cloudflared --image=busybox:1.37 --target=cloudflared
```

## Port-forward

Reach an in-cluster service from the laptop without an IngressRoute:

```bash
kubectl port-forward -n database svc/homelab-db-rw 5432:5432
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090   # Prometheus UI at localhost:9090
```

## Restart, scale, rollout

```bash
kubectl rollout restart -n <ns> deploy/<app>
kubectl rollout status -n <ns> deploy/<app>
kubectl rollout history -n <ns> deploy/<app>
```

```bash
kubectl scale -n <ns> deploy/<app> --replicas=0   # stop an app (Argo CD selfHeal reverts it, see Argo CD below)
```

Since Argo CD runs with `selfHeal: true`, manual changes to managed objects are reverted. To keep a change, commit it to Git.

## Nodes

Kured normally handles drains and reboots. Manual maintenance:

```bash
kubectl cordon balthazar.fferrando.homelab
kubectl drain balthazar.fferrando.homelab --ignore-daemonsets --delete-emptydir-data --timeout=20m
# ... maintenance, reboot ...
kubectl uncordon balthazar.fferrando.homelab
```

```bash
kubectl get nodes -L kubernetes.io/hostname --show-labels
kubectl describe node magi.fferrando.homelab | grep -A3 Taints
```

## Secrets

Read one key, or every key decoded:

```bash
kubectl get secret homelab-db-app -n database -o jsonpath='{.data.password}' | base64 -d; echo
kubectl get secret forgejo-db-credentials -n forgejo \
  -o go-template='{{range $k,$v := .data}}{{$k}}={{$v | base64decode}}{{"\n"}}{{end}}'
```

Initial Argo CD admin password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d; echo
```

## Sealed Secrets

Plain `Secret`s are never committed. Every secret is built locally with `--dry-run`, piped to `kubeseal` and saved as a `SealedSecret` in the app's folder. A sealed secret only decrypts in the **namespace and name** it was sealed for.

**Seal a literal value** (example: Cloudflare tunnel token):

```bash
kubectl create secret generic tunnel-token \
  --namespace cloudflared \
  --from-literal=token="YOUR_TUNNEL_TOKEN" \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --format yaml > infrastructure/cloudflared/sealed-tunnel-token.yaml
```

**Seal a basic-auth (htpasswd) secret** (example: Traefik dashboard; Longhorn works the same way):

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

**Seal app DB credentials** (same password in `database` for the CNPG role and in the app namespace for the pod). The username must match the role name in the app's `db.yaml`:

```bash
APP=hedgedoc; APP_NS=hedgedoc        # kubecraft: APP_NS=minecraft
DB_PW="$(openssl rand -base64 32 | tr -d '/+=')"

seal_db() {  # $1 = namespace, $2 = output file
  kubectl create secret generic "$APP-db-credentials" \
    --namespace "$1" \
    --from-literal=username="$APP" \
    --from-literal=password="$DB_PW" \
    --dry-run=client -o yaml | \
  kubectl label --local -f - cnpg.io/reload=true -o yaml | \
  kubeseal \
    --controller-namespace kube-system \
    --controller-name sealed-secrets \
    --format yaml > "$2"
}

seal_db database  "apps/$APP/db_secret.yaml"
seal_db "$APP_NS" "apps/$APP/deployment_secret.yaml"
# lastgasp lives in infrastructure/: db_secret_database.yaml and db_secret_lastgasp.yaml
```

**Seal a file** (example: lastgasp UI auth file, one `name role hash` line per user, roles `admin`/`viewer`):

```bash
IMG=git.fferrando.cc/rdfilippo/lastgasp-server:latest
docker run --rm -it "$IMG" user admin admin > auth          # prompts for the password
# docker run --rm "$IMG" token grafana viewer >> auth       # optional read-only API token

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

**Update a single key** in an existing sealed file, leaving the other keys untouched:

```bash
echo -n "NEW_VALUE" | kubectl create secret generic kubecraft-secrets \
  --namespace minecraft \
  --from-file=BOOTSTRAP_ADMIN_PASSWORD=/dev/stdin \
  --dry-run=client -o json | \
kubeseal \
  --controller-namespace kube-system \
  --controller-name sealed-secrets \
  --merge-into apps/kubecraft/secrets.yaml
```

**Back up the controller keys** (without them, nothing in Git can be decrypted on a rebuilt cluster). Store the file in the password manager, never in Git:

```bash
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml > sealed-secrets-keys.yaml
# restore on a new cluster: apply it, then restart the controller
kubectl apply -f sealed-secrets-keys.yaml
kubectl rollout restart -n kube-system deploy/sealed-secrets
```

### Secret inventory

| Secret | Namespace | Keys | File | How to generate |
|---|---|---|---|---|
| `cloudflare-api-token-secret` | `cert-manager` | `token` | `infrastructure/traefik/sealed-cloudflare-token.yaml` | Cloudflare API token with DNS edit rights (literal). |
| `tunnel-token` | `cloudflared` | `token` | `infrastructure/cloudflared/sealed-tunnel-token.yaml` | From the Zero Trust tunnel page (literal). |
| `longhorn-auth-secret` | `longhorn-system` | `users` | `infrastructure/longhorn/sealed-longhorn-auth.yaml` | htpasswd. |
| `traefik-dashboard-auth-secret` | `traefik` | `users` | `infrastructure/traefik/sealed-dashboard-auth.yaml` | htpasswd. |
| `<app>-db-credentials` | `database` + app ns | `username`, `password` | `apps/<app>/db_secret.yaml`, `deployment_secret.yaml` | DB credentials recipe. Used by forgejo, hedgedoc, jellyfin, librephoto, vaultwarden, kubecraft, lastgasp. |
| `forgejo-resend-credentials` | `forgejo` | `smtp-user`, `smtp-password` | `apps/forgejo/resend-secrets.yaml` | Resend SMTP credentials (literals). |
| `librephoto-secret-key` | `librephoto` | `secret-key` | `apps/librephoto/secret-key.yaml` | `openssl rand -hex 32`. |
| `kubecraft-secrets` | `minecraft` | `SESSION_SECRET`, `BOOTSTRAP_ADMIN_USER`, `BOOTSTRAP_ADMIN_PASSWORD` | `apps/kubecraft/secrets.yaml` | `SESSION_SECRET` from `openssl rand -hex 32`. The admin must change the password at first login. |
| `kubecraft-playit` | `minecraft` | `SECRET_KEY` | `apps/kubecraft/playit_secret.yaml` | Must be a **self-managed agent** key (dashboard keys are read only). Use the claim script, which writes the Secret to stdout so the key never shows on screen: `~/Desktop/Projects/kubecraft/hack/playit-claim.sh minecraft kubecraft-playit \| kubeseal ... > apps/kubecraft/playit_secret.yaml` |
| `lastgasp-auth` | `lastgasp` | `auth` | `infrastructure/lastgasp/auth_secret.yaml` | Seal-a-file recipe above. |
| `lastgasp-join` | `lastgasp` | `token` | `infrastructure/lastgasp/join_secret.yaml` | Agent enrollment token (literal; see the lastgasp chart docs for its format). |

## Argo CD

```bash
kubectl get applications -n argocd                      # sync + health status of every app
kubectl describe application <app> -n argocd            # last sync errors
```

Force a refresh (re-read Git now instead of waiting for the poll):

```bash
kubectl annotate application <app> -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

With the `argocd` CLI (TLS terminates at Traefik, so use gRPC-web):

```bash
argocd login argocd.internal.fferrando.cc --grpc-web --username admin
argocd app sync <app>
argocd app diff <app>
```

Pause self-heal on an app temporarily, e.g. to scale something by hand:

```bash
kubectl patch application <app> -n argocd --type merge -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}'
```

This is reverted on the next sync of the parent `root-apps`/`root-infrastructure` app. Bootstrap the whole tree (once, on a new cluster):

```bash
kubectl apply -f system/root-app.yaml
```

## Database (CNPG)

Uses the `kubectl cnpg` plugin.

```bash
kubectl cnpg status homelab-db -n database             # primary, replicas, health (see note below)
kubectl get cluster homelab-db -n database -o jsonpath='{.status.currentPrimary}'; echo
kubectl get databases.postgresql.cnpg.io -n database   # per-app databases declared in Git
```

The per-instance section of `cnpg status` (lag, WAL) always shows `Error(s) extracting status`: it goes through the API server pod proxy to port 8000, which `apps/database/networkpolicy.yaml` opens only to the CNPG operator. The cluster-level `Status` line is still accurate.

```bash
kubectl cnpg psql homelab-db -n database -- -d forgejo  # superuser psql session on the primary
kubectl cnpg promote homelab-db homelab-db-2 -n database   # manual switchover
kubectl cnpg restart homelab-db -n database             # rolling restart (replicas first, then switchover)
```

**Dump one database** to the laptop (runs `pg_dump` inside the primary, as `postgres`):

```bash
PRIMARY=$(kubectl get cluster homelab-db -n database -o jsonpath='{.status.currentPrimary}')
kubectl exec -n database "$PRIMARY" -c postgres -- pg_dump -d forgejo > forgejo.sql
```

**Restore a `.sql` dump** as the app's own role, so the restored objects are owned by it:

```bash
# 1. password of the app role
kubectl get secret forgejo-db-credentials -n database -o jsonpath='{.data.password}' | base64 -d; echo

# 2. tunnel to the primary (leave it running)
kubectl port-forward -n database svc/homelab-db-rw 5432:5432

# 3. in another terminal (local psql should be at least the server's major version)
psql -h localhost -p 5432 -U forgejo -d forgejo < forgejo.sql
```

## Storage (Longhorn, PVCs)

```bash
kubectl get pvc -A
kubectl get volumes.longhorn.io -n longhorn-system      # state, robustness, node
kubectl get replicas.longhorn.io -n longhorn-system -o wide
```

Expand a PVC (StorageClasses allow expansion): change `storage:` in the app's YAML and commit. To check progress:

```bash
kubectl describe pvc jellyfin-config -n jellyfin | grep -A5 Conditions
```

## Certificates (cert-manager)

```bash
kubectl get certificates -A                              # READY should be True everywhere
kubectl describe certificate forgejo-internal-tls -n forgejo
kubectl get certificaterequests,orders,challenges -A     # follow a stuck DNS-01 issuance
kubectl logs -n cert-manager deploy/cert-manager --tail=50
```

## Networking and NetworkPolicies

```bash
kubectl get networkpolicy -A
kubectl get ingressroute,ingressroutetcp,middleware -A
kubectl get svc -n traefik                               # exposed entrypoint ports (ServiceLB)
```

Test a connection from inside a namespace (as subject to its NetworkPolicies) with a throwaway pod:

```bash
kubectl run nettest -n forgejo --rm -it --restart=Never --image=busybox:1.37 -- \
  nc -zv homelab-db-rw.database.svc.cluster.local 5432
```

In namespaces enforcing PSS `restricted` (`database`, `cloudflared`, `minecraft`, `portfolio`, `filebrowser`, `hedgedoc`, `jellyfin`, `vaultwarden`, `vibravid`), a bare pod is rejected. Run the test from another namespace, or use `kubectl debug` on an existing pod.

Traefik routing problems:

```bash
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50 | grep -i error
```

## Monitoring and Falco

```bash
kubectl get servicemonitors,podmonitors -A
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090   # then check Status > Targets
```

Falco alerts (one Falco pod per node):

```bash
kubectl logs -n falco -l app.kubernetes.io/name=falco -c falco --tail=100 | grep -v '"priority":"Debug"'
```

## Cleanup and stuck resources

```bash
kubectl delete pod <pod> -n <ns>                              # the controller recreates it
kubectl delete pod <pod> -n <ns> --grace-period=0 --force     # pod stuck in Terminating on a dead node
kubectl get pods -A --field-selector status.phase=Failed      # leftovers from jobs / evictions
kubectl delete pods -A --field-selector status.phase=Failed
```

Object stuck in Terminating because of a finalizer (last resort: understand why the finalizer is not clearing first):

```bash
kubectl patch pvc <pvc> -n <ns> --type merge -p '{"metadata":{"finalizers":null}}'
```
