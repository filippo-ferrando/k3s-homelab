# descheduler

[Kubernetes descheduler](https://github.com/kubernetes-sigs/descheduler). It rebalances pods after kured reboots, which otherwise leave workloads piled onto the nodes that stayed up.

- **Namespace:** `kube-system`

## Files

| File | Wave | Description |
|---|---|---|
| `applications.yaml` | -1 | Argo CD Application for the `descheduler` chart, run as a CronJob every 2 hours. Uses the chart's default policy (RemoveDuplicates, inter-pod anti-affinity violations, LowNodeUtilization 20/50, plus the restart/taint/affinity/topology-spread plugins). |
