# Bootstrapping a new cluster

The full procedure, from bare hosts to a cluster that Argo CD reconciles on its own. Cluster commands are linked to [`../kubectl.md`](../kubectl.md) rather than repeated here.

## 0. Laptop prerequisites

`ansible`, `helm` (the bootstrap renders the Argo CD chart locally), `kubectl`, `kubeseal`, `htpasswd` (`httpd-tools` / `apache2-utils`), `openssl`. Optional: `argocd`, `kubectl-cnpg`.

## 1. Provision hosts and k3s (Ansible)

```bash
ansible-playbook -i ansible/inventory.ini ansible/01_os_prep.yml          # packages, SELinux, firewall, iSCSI/NFS clients, Tailscale
ansible-playbook -i ansible/inventory.ini ansible/02_bootstrap_cluster.yml # k3s HA (3 servers + casper agent) + Argo CD
ansible-playbook -i ansible/inventory.ini ansible/04_deploy_nfs_shares.yml # NFS exports on casper
ansible-playbook -i ansible/inventory.ini ansible/03_deploy_borg_backups.yml
```

Then fetch the kubeconfig: [kubectl.md#access](../kubectl.md#access).

## 2. Restore or create the Sealed Secrets key

- **Rebuilding** an existing homelab: apply the backed-up controller keys **before** step 3, so every SealedSecret in Git decrypts as-is ([kubectl.md#sealed-secrets](../kubectl.md#sealed-secrets), "Back up the controller keys").
- **Brand-new cluster:** skip this step. The controller generates a new key, and every secret has to be re-sealed in step 4.

## 3. Start GitOps

```bash
kubectl apply -f system/root-app.yaml
```

The Argo CD admin password is in [kubectl.md#secrets](../kubectl.md#secrets). The UI is at `https://argocd.internal.fferrando.cc` once Traefik and cert-manager are up. Until then, use `kubectl port-forward -n argocd svc/argocd-server 8080:80`.

Sync order follows the sync waves: sealed-secrets and Longhorn (-4), Traefik/cert-manager/CNPG (-3), kured and the device plugin (-2), monitoring/descheduler and sealed secrets (-1), then apps (`root-apps` at wave 1, per-app waves 0 to 6).

On a brand-new cluster, `cert-manager`, `cloudflared` and the Longhorn/Traefik dashboards stay degraded until their secrets exist. This is expected.

## 4. Seal and push secrets (brand-new cluster only)

Use the recipes and the full inventory in [kubectl.md#sealed-secrets](../kubectl.md#sealed-secrets). The minimum to get the core healthy:

1. `cloudflare-api-token-secret` (cert-manager DNS-01)
2. `tunnel-token` (cloudflared)
3. `longhorn-auth-secret`, `traefik-dashboard-auth-secret`

Then every app's DB credentials and app-specific secrets. Commit and push. Argo CD picks them up and the degraded apps converge.

## 5. Verify

[kubectl.md#argo-cd](../kubectl.md#argo-cd) (all apps `Synced`/`Healthy`) and [kubectl.md#certificates-cert-manager](../kubectl.md#certificates-cert-manager) (all certificates `READY`).

| Service | URL | Notes |
|---|---|---|
| Argo CD | `argocd.internal.fferrando.cc` | admin password from `argocd-initial-admin-secret` |
| Traefik dashboard | `traefik.internal.fferrando.cc` | basic auth |
| Longhorn | `longhorn.internal.fferrando.cc` | basic auth |
| Grafana | `stats.internal.fferrando.cc` | `admin`/`admin`, change at first login |
| Grafana public | `status.fferrando.cc` | shared dashboards only |
| Pushgateway | `pushgateway.internal.fferrando.cc` | Borg backup metrics |
| lastgasp | `lastgasp.internal.fferrando.cc` | |
| Forgejo | `git.internal.fferrando.cc` / `git.fferrando.cc` | SSH on port 2222 |
| Jellyfin | `jellyfin.internal.fferrando.cc` / `jellyfin.fferrando.cc` | |
| LibrePhotos | `photo.internal.fferrando.cc` / `photo.fferrando.cc` | |
| FileBrowser | `files.internal.fferrando.cc` / `files.fferrando.cc` | |
| Vaultwarden | `vault.internal.fferrando.cc` | LAN only |
| vibravid | `download.internal.fferrando.cc` | LAN only |
| HedgeDoc | `doc.fferrando.cc` | public only |
| kubecraft | `mine.fferrando.cc` | public only |
| Portfolio | `fferrando.cc` | public only |
