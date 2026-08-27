```bash
mkdir -p ~/.kube
scp magi@192.168.10.100:/etc/rancher/k3s/k3s.yaml ~/.kube/config
sed -i 's/127.0.0.1/192.168.10.100/g' ~/.kube/config
kubectl get nodes
```
