# sealed-secrets

[Bitnami Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) controller. Every secret in this repo is committed as an encrypted `SealedSecret`, and only this controller can decrypt it.

- **Namespace:** `kube-system`

## Files

| File | Wave | Description |
|---|---|---|
| `application.yaml` | -4 | Argo CD Application for the `sealed-secrets` chart, with memory limits. Synced first, because sealed secrets elsewhere use wave -1/0. |

The controller's private key is the only way to decrypt the repo's secrets: back it up, since a rebuilt cluster without it means re-sealing everything. How to back up the key and seal a secret: `notes/kubectl.md#sealed-secrets`.
