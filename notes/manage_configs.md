### Part 2: Modifying `app.ini` via GitOps

To manage application configuration files without logging into containers, you have two options in Kubernetes.

#### Option A: The Environment Variable Method (Recommended)

Forgejo is designed for containers, meaning it can translate environment variables directly into `app.ini` settings on the fly. This is the cleanest GitOps approach because your configuration lives right inside your `deployment.yaml`.

The syntax is `FORGEJO__<section_name>__<key_name>`.

```yaml
# apps/forgejo/deployment.yaml (Inside the env: block)
          env:
            # Translates to [server] DOMAIN = git.fferrando.cc
            - name: FORGEJO__server__DOMAIN
              value: "git.fferrando.cc"
            
            # Translates to [server] ROOT_URL = https://git.fferrando.cc/
            - name: FORGEJO__server__ROOT_URL
              value: "https://git.fferrando.cc/"
              
            # Translates to [mailer] ENABLED = true
            - name: FORGEJO__mailer__ENABLED
              value: "true"

```

#### Option B: The ConfigMap Method (For complex files)

If you have a massive `app.ini` file and prefer to keep it as a raw file, you wrap the file in a Kubernetes `ConfigMap` and "mount" it into the pod.

**1. Create the ConfigMap Manifest (`apps/forgejo/configmap.yaml`)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: forgejo-config
  namespace: forgejo
data:
  app.ini: |
    APP_NAME = "Filippo's Forgejo"
    RUN_MODE = prod

    [server]
    DOMAIN = git.fferrando.cc
    ROOT_URL = https://git.fferrando.cc/
    HTTP_PORT = 3000

```

**2. Mount it in your Deployment (`apps/forgejo/deployment.yaml`)**
You instruct Kubernetes to take that ConfigMap and project it as a physical file inside the container's filesystem.

```yaml
      containers:
        - name: forgejo
          volumeMounts:
            - name: data
              mountPath: /data
            - name: config-volume
              mountPath: /data/gitea/conf/app.ini # Forgejo reads from here
              subPath: app.ini
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: forgejo-data
        - name: config-volume
          configMap:
            name: forgejo-config

```

When you commit this to GitHub, Argo CD applies the ConfigMap and restarts the Forgejo pod. The pod boots up, sees the `app.ini` file exactly where it belongs, and applies your settings. If you ever need to change a setting, you just edit the `configmap.yaml` in GitHub, and Argo CD updates the cluster automatically.
