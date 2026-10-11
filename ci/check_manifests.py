#!/usr/bin/env python3
"""Repo policy checks for the manifests under apps/, infrastructure/ and system/.

Fails (exit 1) on:
  secret      a plaintext Secret with data (commit a SealedSecret instead)
  image       a container image without a pinned version tag (missing, latest, or no digit in the tag)
  limits      a container without resources.limits.memory
  privileged  a privileged container outside ALLOW_PRIVILEGED
  netpol      a Namespace defined here with no NetworkPolicy here, unless a Helm Application deploys into it
              (the chart then ships its own policies)

Usage: python3 ci/check_manifests.py [repo-root]
"""
import pathlib
import sys

import yaml

ROOTS = ("apps", "infrastructure", "system")
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod"}
# Argo CD repository Secrets may be committed when they carry no credentials
REPO_SECRET_SAFE_KEYS = {"name", "type", "url", "enableOCI", "project"}
# kind/namespace/name -> reason
ALLOW_PRIVILEGED = {
    "DaemonSet/kube-system/generic-device-plugin": "needs host /dev and the kubelet device-plugin socket",
}


def load(root):
    for path in sorted(p for r in ROOTS for p in (root / r).rglob("*.y*ml")):
        try:
            docs = list(yaml.safe_load_all(path.read_text()))
        except yaml.YAMLError as e:
            yield path, None, f"invalid YAML: {e}"
            continue
        for doc in docs:
            # Helm values files and other plain YAML have no kind: not manifests
            if isinstance(doc, dict) and "kind" in doc and "apiVersion" in doc:
                yield path, doc, None


def pod_spec(doc):
    spec = doc.get("spec") or {}
    if doc["kind"] == "Pod":
        return spec
    if doc["kind"] == "CronJob":
        spec = (spec.get("jobTemplate") or {}).get("spec") or {}
    return (spec.get("template") or {}).get("spec") or {}


def check(root):
    errors = []
    namespaces, netpol_ns, helm_app_ns = {}, set(), set()

    for path, doc, err in load(root):
        rel = path.relative_to(root)
        if err:
            errors.append(f"{rel}: {err}")
            continue
        kind, meta = doc["kind"], doc.get("metadata") or {}
        name, ns = meta.get("name", "?"), meta.get("namespace", "")
        ref = f"{rel}: {kind}/{name}"

        if kind == "Secret" and (doc.get("data") or doc.get("stringData")):
            keys = set(doc.get("data") or {}) | set(doc.get("stringData") or {})
            is_repo = (meta.get("labels") or {}).get("argocd.argoproj.io/secret-type") == "repository"
            if not (is_repo and keys <= REPO_SECRET_SAFE_KEYS):
                errors.append(f"{ref} [secret] plaintext Secret with keys {sorted(keys)}: commit a SealedSecret")

        elif kind == "Namespace":
            namespaces[name] = rel
        elif kind == "NetworkPolicy":
            netpol_ns.add(ns)
        elif kind == "Application":
            spec = doc.get("spec") or {}
            sources = spec.get("sources") or [spec.get("source") or {}]
            if any("chart" in s for s in sources):
                helm_app_ns.add((spec.get("destination") or {}).get("namespace"))

        elif kind in WORKLOADS:
            spec = pod_spec(doc)
            for c in (spec.get("initContainers") or []) + (spec.get("containers") or []):
                cref = f"{ref} container {c.get('name')}"
                image = c.get("image", "")
                tag = image.rsplit(":", 1)[1] if ":" in image.rsplit("/", 1)[-1] else ""
                if "@sha256:" not in image and (tag in ("", "latest") or not any(ch.isdigit() for ch in tag)):
                    errors.append(f"{cref} [image] '{image}' is not pinned to a version tag")
                if not ((c.get("resources") or {}).get("limits") or {}).get("memory"):
                    errors.append(f"{cref} [limits] no resources.limits.memory")
                if (c.get("securityContext") or {}).get("privileged") and f"{kind}/{ns}/{name}" not in ALLOW_PRIVILEGED:
                    errors.append(f"{cref} [privileged] privileged container (allowlist it in ALLOW_PRIVILEGED with a reason)")

    for ns, rel in sorted(namespaces.items()):
        if ns not in netpol_ns and ns not in helm_app_ns:
            errors.append(f"{rel}: Namespace/{ns} [netpol] no NetworkPolicy in this namespace")
    return errors


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = check(root)
    for e in errors:
        print(f"::error::{e}")
    print(f"{len(errors)} policy violation(s)")
    sys.exit(1 if errors else 0)
