# Jellyfin access from the main home LAN

Goal: let devices on the main home LAN (`192.168.1.0/24`, behind the ISP router), e.g. a TV,
reach `jellyfin.internal.fferrando.cc` directly instead of going through the Cloudflare Tunnel.

```
TV (192.168.1.x)
  -> DNS: jellyfin.internal.fferrando.cc = OPNsense WAN IP (192.168.1.x)
  -> OPNsense WAN :443  --port forward-->  192.168.10.102:8444
  -> Traefik entrypoint "home-lan"  -> jellyfin-internal IngressRoute -> jellyfin:8096
```

Only Jellyfin is bound to the `home-lan` entrypoint, so no other `*.internal` service is
reachable from the main LAN.

## 1. Cluster (repo)

`infrastructure/traefik/values.yaml` — add a dedicated entrypoint under `ports:`:

```yaml
  # Main home LAN (192.168.1.0/24) via OPNsense WAN port forward 443 -> node:8444
  home-lan:
    port: 8444
    expose:
      default: true
    exposedPort: 8444
```

`apps/jellyfin/ingressroute.yaml` — attach `jellyfin-internal` to it:

```yaml
spec:
  entryPoints:
    - websecure
    - home-lan
```

Commit + push, let Argo CD sync, then verify from the homelab network:

```bash
curl -k --resolve jellyfin.internal.fferrando.cc:8444:192.168.10.102 \
  https://jellyfin.internal.fferrando.cc:8444
```

## 2. OPNsense

1. **Interfaces → WAN**: uncheck **Block private networks** (the main LAN is RFC1918).
2. **Firewall → NAT → Port Forward** → add:

   | Field | Value |
   |---|---|
   | Interface | `WAN` |
   | Protocol | `TCP` |
   | Source | `192.168.1.0/24` |
   | Destination | `WAN address` |
   | Destination port | `443` |
   | Redirect target IP | `192.168.10.102` (any k3s node works, ServiceLB listens on all) |
   | Redirect target port | `8444` |
   | Filter rule association | `Add associated filter rule` |

No NAT reflection needed: homelab clients keep resolving to the internal IP via AdGuard.

## 3. DNS (Cloudflare)

Add a record:

| Type | Name | Content | Proxy |
|---|---|---|---|
| `A` | `jellyfin.internal` | OPNsense WAN IP (`192.168.1.x`) | **DNS only** (grey cloud) |

AdGuard's local rewrite for `*.internal.fferrando.cc` still wins for homelab / Tailscale clients.

## 4. Client

On the TV, set the Jellyfin server to `https://jellyfin.internal.fferrando.cc`.

## Troubleshooting

- **Name doesn't resolve on the main LAN** → the ISP router likely has DNS rebind protection
  (drops public answers containing private IPs). Workaround: add a WAN port forward for
  `53` TCP/UDP (source `192.168.1.0/24`) to AdGuard, and set the TV's DNS manually to the
  OPNsense WAN IP.
- **Connection refused / timeout** → check the port forward + "Block private networks",
  and that `kubectl -n traefik get svc` shows port `8444` exposed.
