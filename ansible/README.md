# ansible

Host provisioning and day-2 maintenance. Every playbook is idempotent: a second run on a converged node reports no changes. Run from the repo root:

```bash
ansible-playbook -i ansible/inventory.ini ansible/<playbook>.yml --ask-vault-pass
```

`--limit <host>` works on every playbook. For risky changes (firewall), try one node first.

## Entry points

| Playbook | What it does |
|---|---|
| `site.yml` | Full install of a new cluster: imports `provision/01..07` in order. |
| `patch_cluster.yml` | `maintenance/patch_os.yml`, then `maintenance/upgrade_k3s.yml`. |

## provision/

| Playbook | Hosts | What it does |
|---|---|---|
| `01_os.yml` | all | Full `dnf` update, required packages (SELinux, iSCSI, NFS client, cockpit, zram, epel), SELinux booleans, kernel modules, sysctls, zram, `iscsid`. |
| `02_firewall.yml` | all | firewalld: trusts only the pod/service CIDRs, the node IPs and `tailscale0`; the rest of the LAN gets `ssh`, `cockpit`, `6443` and the ServiceLB ports. Also removes the old whole-LAN trust and LAN-open node ports. |
| `03_tailscale.yml` | all | Installs Tailscale, enables Tailscale SSH, sets the operator and turns off its netfilter management, changing only what differs from the current prefs. `tailscale up` stays manual. |
| `04_k3s.yml` | servers, agents | Installs k3s `k3s_version` (HA embedded etcd, SELinux, nftables kube-proxy, bundled Traefik disabled) on nodes that don't have it yet, and writes `secrets-encryption: true` to `/etc/rancher/k3s/config.yaml` on every server. Prints the secrets encryption status. |
| `05_argocd.yml` | first server | Bootstrap only: if Argo CD is missing, renders the chart from `infrastructure/argocd/` with local `helm` and applies it. Skipped once Argo CD exists, since it then manages itself. |
| `06_nfs.yml` | all, `nfs_storage` | `nfs-utils` everywhere. On casper: exports (rw shares to the node IPs only, `/mnt/vault` read-only to `borg_backup`), `nfs-server`, NFS closed to the rest of the LAN. |
| `07_backups.yml` | `borg_backup` | Installs EPEL and `borgbackup`, sets the passphrase file (`/home/magi/.bak_psw`, never in Git) to `0600`, mounts `/mnt/vault` read-only at `/mnt/casper-data`, deploys `scripts/borg_backup_personal.sh` and its cron job. |

## maintenance/

| Playbook | What it does |
|---|---|
| `patch_os.yml` | `dnf update` on every node, and creates `/var/run/reboot-required` for Kured when `needs-restarting -r` asks for a reboot. |
| `upgrade_k3s.yml` | One node at a time, servers first: downloads the `k3s_version` binary (checksum-verified, skipped when it already matches), restarts k3s, and waits until the node is Ready on the new version. No drain: pods keep running across a k3s restart. |
| `prune_images.yml` | `crictl rmi --prune` on every node. |

## Other files

| File | Description |
|---|---|
| `inventory.ini` | Nodes and groups: `k3s_servers`, `k3s_agents`, `k3s_cluster`, `nfs_storage`, `borg_backup`. |
| `group_vars/all.yml` | Vaulted become password, `k3s_version` (bumped by Renovate, one Kubernetes minor at a time), pod and service CIDRs. |
| `scripts/borg_backup_personal.sh` | Borg create/prune/compact of `/mnt/casper-data` into `/mnt/data/backup-casper` (passphrase through `BORG_PASSCOMMAND`), metrics pushed to the Pushgateway. Exits non-zero on failure. |

**Laptop prerequisites:** `ansible` (with `ansible.posix` and `community.general`), `helm` (for `05_argocd.yml`).
