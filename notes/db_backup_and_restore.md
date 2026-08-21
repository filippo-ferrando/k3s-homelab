### Part 1: Migrating the `.sql` Database Dump

Because CloudNativePG acts as a secure, closed loop, you cannot just drop a file into a folder. Instead, you create a temporary tunnel from your laptop directly to the primary database pod and stream the `.sql` file over the network.

**1. Retrieve the Database Password**
CloudNativePG automatically generated this during bootstrap. Extract it to your local terminal:

```bash
kubectl get secret homelab-db-app -n database -o jsonpath="{.data.password}" | base64 -d; echo

```

**2. Open a Network Tunnel (Port-Forwarding)**
Open a direct tunnel to the Read-Write (`-rw`) service of your database cluster:

```bash
kubectl port-forward svc/homelab-db-rw -n database 5432:5432

```

**3. Run the Import Locally**
Leave the tunnel running, open a *new* terminal tab on your laptop, and use the standard `psql` client to push your dump into the cluster:

```bash
# Provide the password from step 1 when prompted
psql -h localhost -p 5432 -U app_user -d forgejo < /path/to/your/forgejo_dump.sql

```

Once it finishes, close the tunnel. Your HA database is now fully populated!
