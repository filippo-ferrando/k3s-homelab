# kured

[Kured](https://kured.dev) reboots nodes one at a time when `/var/run/reboot-required` appears. That sentinel file is created after OS updates by `ansible/patch_cluster.yml`.

- **Namespace:** `kube-system`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -2 | Argo CD Application for the `kubereboot/kured` chart, with values from this repo. |
| `values.yaml` | - | Reboot window 01:00 to 05:00 Europe/Rome, every day, checked every 15m. Long drain (20m grace/timeout) for Longhorn volume handoff and CNPG failover. `drainPodSelector` skips Longhorn instance-manager and CSI pods, whose PDBs can block a drain forever (longhorn/longhorn#5910). Lock TTL 1h so a hung node can't deadlock the cluster. Tolerates the control-plane taint (`magi`). Metrics go to `monitoring`. |
