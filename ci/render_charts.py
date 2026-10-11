#!/usr/bin/env python3
"""Render every Helm-based Argo CD Application in the repo, the way Argo CD would.

For each Application under apps/ and infrastructure/ with a `chart` source, runs `helm template`
with the same chart, version, release name, namespace and values (valueFiles from this repo,
valuesObject, values, parameters), and writes the output to <out-dir>/<app>.yaml.
A chart that fails to render (bad values, removed version, schema error) fails the run.

Usage: python3 ci/render_charts.py <out-dir> [repo-root]
"""
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

# Optional CRDs that charts probe with .Capabilities before creating ServiceMonitors etc.
API_VERSIONS = ["monitoring.coreos.com/v1"]


def applications(root):
    for path in sorted(p for r in ("apps", "infrastructure") for p in (root / r).rglob("*.y*ml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if isinstance(doc, dict) and doc.get("kind") == "Application":
                spec = doc["spec"]
                for src in spec.get("sources") or [spec.get("source") or {}]:
                    if "chart" in src:
                        yield doc["metadata"]["name"], spec["destination"]["namespace"], src


def kube_version(root):
    # The cluster version, so charts with a kubeVersion constraint render as on the real cluster
    m = re.search(r"^k3s_version:\s*v?(\d+\.\d+\.\d+)", (root / "ansible/group_vars/all.yml").read_text(), re.M)
    return m.group(1) if m else None


def render(root, out, name, namespace, src, tmp):
    helm = src.get("helm") or {}
    repo = src["repoURL"]
    if "://" in repo:
        chart_args = [src["chart"], "--repo", repo]
    else:
        # Argo CD OCI repositories are written without a scheme (see infrastructure/lastgasp/repository.yaml)
        chart_args = [f"oci://{repo}/{src['chart']}"]

    cmd = ["helm", "template", helm.get("releaseName", name), *chart_args,
           "--version", str(src["targetRevision"]), "--namespace", namespace, "--include-crds"]
    if kv := kube_version(root):
        cmd += ["--kube-version", kv]
    for api in API_VERSIONS:
        cmd += ["--api-versions", api]
    for vf in helm.get("valueFiles") or []:
        cmd += ["--values", str(root / vf.removeprefix("$values/"))]
    for key, content in (("valuesObject", yaml.safe_dump(helm["valuesObject"]) if "valuesObject" in helm else None),
                         ("values", helm.get("values"))):
        if content:
            f = pathlib.Path(tmp) / f"{name}-{key}.yaml"
            f.write_text(content)
            cmd += ["--values", str(f)]
    for p in helm.get("parameters") or []:
        cmd += ["--set", f"{p['name']}={p['value']}"]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(f"::error::{name}: helm template failed: {r.stderr.strip()}")
        return False
    (out / f"{name}.yaml").write_text(r.stdout)
    print(f"rendered {name} ({src['chart']} {src['targetRevision']})")
    return True


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    root = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        results = [render(root, out, *app, tmp) for app in applications(root)]
    print(f"{results.count(True)} chart(s) rendered, {results.count(False)} failed")
    sys.exit(0 if all(results) else 1)
