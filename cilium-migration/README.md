# flannel → Cilium migration runbook

Scope: in-place, per-node hot-swap. No data-plane risk (Longhorn/etcd/CNPG
untouched) -- only pod networking is affected, one node at a time.
Full kube-proxy replacement + Cilium LB IPAM (replacing servicelb) + Hubble UI.

## Order of operations

0. **Pre-flight** (read-only): `ansible-playbook -i ../ansible/inventory.ini playbooks/00_preflight.yml`
   Record the Traefik LB IP it prints -- you need it for `manifests/loadbalancer-ippool.yaml`
   and a pinned annotation in `infrastructure/traefik/values.yaml` later.

1. **Open firewalld ports** (safe anytime): `ansible-playbook -i ../ansible/inventory.ini playbooks/02_firewalld_cilium.yml`

2. **Manual step -- install Cilium once, on casper, via cilium-cli** (not automated;
   cilium-cli auto-detects k3s's CNI paths correctly, which is worth doing
   interactively rather than guessing in a playbook):
   ```bash
   cilium install --version 1.20.2 \
     --set kubeProxyReplacement=true \
     --set k8sServiceHost=127.0.0.1 --set k8sServicePort=6444 \
     --set routingMode=native --set autoDirectNodeRoutes=true \
     --set ipv4NativeRoutingCIDR=10.42.0.0/16 \
     --set ipam.mode=kubernetes \
     --set socketLB.hostNamespaceOnly=true \
     --set securityContext.privileged=true \
     --set l2announcements.enabled=true \
     --set hubble.relay.enabled=true --set hubble.ui.enabled=true
   cilium install --dry-run-helm-values > manifests/values.yaml   # reconcile against the placeholder already there
   ```
   Apply `manifests/loadbalancer-ippool.yaml` and `manifests/l2-announcement-policy.yaml`
   (adjust CIDR/interface first) once Cilium is up:
   ```bash
   kubectl apply -f manifests/loadbalancer-ippool.yaml
   kubectl apply -f manifests/l2-announcement-policy.yaml
   ```

3. **Migrate nodes one at a time, in this order: casper -> balthazar -> caelium -> magi.**
   ```bash
   ansible-playbook -i ../ansible/inventory.ini playbooks/01_migrate_node.yml -e target_node=casper.fferrando.homelab
   # verify (see below) before continuing
   ansible-playbook -i ../ansible/inventory.ini playbooks/01_migrate_node.yml -e target_node=balthazar.fferrando.homelab
   # verify, confirm Longhorn Robustness=Healthy before continuing
   ansible-playbook -i ../ansible/inventory.ini playbooks/01_migrate_node.yml -e target_node=caelium.fferrando.homelab
   # verify, confirm Longhorn Robustness=Healthy before continuing
   ansible-playbook -i ../ansible/inventory.ini playbooks/01_migrate_node.yml -e target_node=magi.fferrando.homelab
   ```
   **casper's successful, fully-verified migration is the real go/no-go gate** --
   mixed flannel/Cilium across multiple nodes is not a supported state, so past
   casper there is no clean single-node rollback, only "finish migrating forward."
   Before draining a *server* node, confirm etcd health:
   `k3s kubectl get --raw /readyz?verbose | grep etcd` (and optionally
   `k3s etcd-snapshot ls` / take a fresh snapshot). Never drain a second server
   until the previous one is fully back and Longhorn volumes are Healthy again.

4. **Verify end-to-end** (after all 4 nodes):
   ```bash
   cilium status --wait
   cilium connectivity test
   kubectl get volumes.longhorn.io -n longhorn-system -o custom-columns=NAME:.metadata.name,ROBUSTNESS:.status.robustness,STATE:.status.state
   kubectl get pods -n longhorn-system
   kubectl get clusters.postgresql.cnpg.io -A
   kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'   # compare to Phase 0 value
   curl -sSI https://traefik.internal.fferrando.cc
   curl -sSI https://longhorn.internal.fferrando.cc   # expect 401, not a connection failure
   ```
   NetworkPolicy enforcement check (this policy was previously a no-op under
   flannel -- confirm it's now actually enforced):
   ```bash
   # should succeed (Prometheus is in scope)
   kubectl exec -n monitoring deploy/kube-prometheus-stack-prometheus -c prometheus -- \
     wget -qO- --timeout=3 http://<longhorn-manager-pod-ip>:9500/metrics | head -1
   # should now block
   kubectl run netpol-test --rm -it --image=busybox --restart=Never -- \
     wget -qO- --timeout=3 http://<longhorn-manager-pod-ip>:9500/metrics
   ```

5. **Adopt into GitOps** once everything above is green:
   - Follow `notes/kubeseal_secrets.md` to create `hubble-auth-secret`, add the
     resulting `sealed-hubble-auth.yaml` to `manifests/`.
   - Pin Traefik's LB IP: add `service.annotations: {io.cilium/lb-ipam-ips: "<captured IP>"}`
     to `infrastructure/traefik/values.yaml`.
   - Copy `cilium-migration/manifests/*` into a new `infrastructure/cilium/` folder in the repo.
   - Commit. `root-infrastructure` (already `directory.recurse:true`, `automated: {prune:true, selfHeal:true}`)
     picks it up automatically -- it should show a clean sync against the already-running release.
   - Update `ansible/02_bootstrap_cluster.yml` (remove `--flannel-iface`,
     `--kube-proxy-arg=proxy-mode=nftables`; add `--flannel-backend=none`,
     `--disable-network-policy`, `--disable-kube-proxy`, `--disable servicelb`
     to the server blocks; add `--disable-kube-proxy` only to the agent block)
     so a from-scratch re-provision matches the now-live cluster.
   - Fold `playbooks/02_firewalld_cilium.yml`'s tasks into `ansible/01_os_prep.yml`'s
     existing "Allow K3s ports" task for the same reason.

## Rollback

Only clean while casper is the sole migrated node: `ansible-playbook -i ../ansible/inventory.ini playbooks/99_rollback_node.yml -e target_node=casper.fferrando.homelab`.
No data-loss risk either way (Longhorn/etcd untouched) -- a botched rollback is a
networking outage, resolved by finishing the migration in whichever direction.

## Known risks (validate, don't assume)

1. **SELinux enforcing + Cilium's default container** is a documented upstream
   failure mode (`cilium/cilium#34068`) -- `securityContext.privileged: true`
   is the mitigation above, but confirm on casper under enforcing mode before
   trusting it on any server:
   ```bash
   ausearch -m avc -ts recent | grep -i cilium   # only if privileged:true still fails
   audit2allow -a -M cilium-local                # fallback: generate + semodule -i
   ```
   Do not proceed past casper until this is enforcing-clean.
2. Confirm `--disable-kube-proxy` is accepted by your installed k3s's `k3s agent`
   subcommand (`k3s agent --help | grep -i kube-proxy` on casper) before relying on it.
3. `k8sServiceHost=127.0.0.1:6444` depends on k3s's local apiserver LB proxy
   existing on agents too -- confirmed by `00_preflight.yml`'s port-6444 check.
4. If `kubectl exec`/`kubectl logs -f` against pods on remote nodes breaks after
   kube-proxy removal, add `--egress-selector-mode=cluster` to the k3s server
   flags -- not pre-emptively added, only if this symptom appears during verification.
