# ci

Checks that run on every push to `main` and every pull request (Renovate's included), defined in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). They catch a broken or unsafe change before Argo CD applies it to the cluster.

## Jobs

| Job | Blocking | What it checks |
|---|---|---|
| `secrets` | yes | gitleaks over the **full Git history** (the repo is public, so anything ever committed is exposed). SealedSecret ciphertext is allowed by [`.gitleaks.toml`](../.gitleaks.toml); everything else uses the default rules. |
| `policy` | yes | `check_manifests.py`: no plaintext `Secret`, every image pinned to a version tag, every container with `resources.limits.memory`, no privileged container outside an allowlist, a NetworkPolicy in every Namespace defined in the repo. |
| `manifests` | yes | kubeconform, strict, on every manifest under `apps/`, `infrastructure/` and `system/`. Custom resources are validated against the [CRDs catalog](https://github.com/datreeio/CRDs-catalog); a resource without a schema fails instead of being skipped. |
| `charts` | yes | `render_charts.py` renders every Helm-based Application with its chart, version and values, as Argo CD would, then kubeconform validates the output. Catches Renovate chart bumps that break with the repo's values. |
| `ansible` | yes | `ansible-playbook --syntax-check` on `site.yml`, `patch_cluster.yml` and `maintenance/prune_images.yml`, with the collections from `ansible/requirements.yml`. No vault password or node access needed. |
| `misconfig` | no | trivy config scan, uploaded to the GitHub Security tab (code scanning). Report-only, because the known findings (root containers, writable root filesystems) are tracked in `notes/security/`. New findings show up as PR annotations. |

## Files

| File | Description |
|---|---|
| `check_manifests.py` | Repo policy checks (see the `policy` job). Allowlists live at the top of the file, each with a reason. |
| `render_charts.py` | Renders every chart Application into `<out-dir>/<app>.yaml` with `helm template`. Uses the cluster's Kubernetes version from `ansible/group_vars/all.yml`. |

## Running locally

Same commands as CI, from the repo root (needs `python3` with PyYAML, `helm`, `gitleaks`, `kubeconform`):

```bash
gitleaks git --config .gitleaks.toml --redact .
python3 ci/check_manifests.py
kubeconform -strict -summary -ignore-filename-pattern 'values\.yaml$' \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  apps infrastructure system
python3 ci/render_charts.py /tmp/rendered
kubeconform -strict -summary -skip CustomResourceDefinition \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  /tmp/rendered
```

## Supply chain

- Actions are pinned to commit SHAs (with the version in a comment); tools run from their official images at exact tags (`docker://ghcr.io/...`). Renovate updates both, plus the `pip install` pins and the Helm version (custom managers in `renovate.json`).
- The workflow token is read-only (`contents: read`); only `misconfig` gets `security-events: write` to upload its report. Checkouts don't persist credentials.

## Required checks

Make the blocking jobs required in the `main` branch protection (GitHub: Settings > Branches > `main` > Require status checks): `secrets`, `policy`, `manifests`, `charts`, `ansible`. Without that, a red check doesn't stop a merge.
