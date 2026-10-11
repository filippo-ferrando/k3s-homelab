# generic-device-plugin

[squat/generic-device-plugin](https://github.com/squat/generic-device-plugin) exposes the host's `/dev/kmsg` as the extended resource `devic.es/kmsg`. The lastgasp agent requests that resource and gets the device without running privileged.

- **Namespace:** `kube-system`

## Files

| File | Wave | Description |
|---|---|---|
| `daemonset.yaml` | -2 | DaemonSet on every node (tolerates all taints, `system-node-critical`). It is privileged by necessity, because it needs host `/dev` and the kubelet device-plugin socket. Synced before lastgasp (wave 5) so the resource exists when the agents start. |
