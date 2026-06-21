# MCP services gateway (GCP `mcp-services`)

Always-on HTTPS MCP gateway at **`https://mcp.seehart.com`** for Claude.ai mobile connectors.

## Architecture

| Path | Port | Service |
|------|------|---------|
| `/host/` | 8754 | Host MCP (sites, deploy, inventory) |
| `/tesla/` | 8752 | Tesla Fleet MCP |
| `/fish/` | 8753 | Fish email MCP |
| `/agent/` | 8755 | Bridge MCP (Cursor cloud agents) |
| `/nfnc/` | 8756 | NFNC Sheets MCP |

Public: **HTTPS only** (nginx + Let's Encrypt). MCP apps bind **127.0.0.1**; GCP firewall blocks 8752–8756 externally.

## One-time VM bootstrap

`compute` manages start/stop of an **existing** GCE VM. Create it once:

```bash
export GCP_PROJECT=your-project
gcloud compute instances create mcp-services \
  --project=$GCP_PROJECT \
  --zone=us-central1-a \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --tags=mcp-services

gcloud compute firewall-rules create allow-mcp-https \
  --project=$GCP_PROJECT \
  --allow=tcp:443 \
  --target-tags=mcp-services \
  --source-ranges=0.0.0.0/0

gcloud compute firewall-rules create allow-mcp-ssh-iap \
  --project=$GCP_PROJECT \
  --allow=tcp:22 \
  --target-tags=mcp-services \
  --source-ranges=35.235.240.0/20
```

On the VM (via `compute ssh mcp-services`):

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx python3-venv git
sudo useradd -m -s /bin/bash mcp || true
sudo mkdir -p /var/log/mcp-audit && sudo chown mcp:mcp /var/log/mcp-audit
```

DNS: **`mcp.seehart.com` A record** → VM external IP.

TLS: `sudo certbot --nginx -d mcp.seehart.com`

Bind SSH: `compute bind mcp-services` (after first successful IAP ssh).

## Secrets (on laptop, sync to VM)

Set in `~/.config/ken/host/host.env` and per-service env files under `~/.config/`:

| Variable | Service |
|----------|---------|
| `HOST_MCP_CLIENT_SECRET` | host |
| `FISH_MCP_CLIENT_SECRET` | fish |
| `MCP_CLIENT_SECRET` | tesla |
| `NFNC_MCP_CLIENT_SECRET` | nfnc |
| `BRIDGE_MCP_CLIENT_SECRET` | bridge |
| `CURSOR_API_KEY` | bridge (`~/.config/bridge/secrets.yaml`) |

Gateway base URLs (on VM env files):

```
HOST_MCP_BASE_URL=https://mcp.seehart.com/host
FISH_MCP_BASE_URL=https://mcp.seehart.com/fish
MCP_BASE_URL=https://mcp.seehart.com/tesla
NFNC_MCP_BASE_URL=https://mcp.seehart.com/nfnc
BRIDGE_MCP_BASE_URL=https://mcp.seehart.com/agent
MCP_GATEWAY=1
```

All `*_MCP_HOST=127.0.0.1` (default).

## Deploy

```bash
compute up mcp-services
sitehost deploy-mcp-gateway --dry-run   # preflight secrets
sitehost deploy-mcp-gateway
sitehost verify-mcp-gateway
```

## Claude.ai connectors (manual)

Register five custom MCP connectors in Claude settings:

| Name | URL |
|------|-----|
| Ken Host | `https://mcp.seehart.com/host/mcp` |
| Ken Tesla | `https://mcp.seehart.com/tesla/mcp` |
| Ken Fish | `https://mcp.seehart.com/fish/mcp` |
| Ken NFNC | `https://mcp.seehart.com/nfnc/mcp` |
| Ken Agent | `https://mcp.seehart.com/agent/mcp` |

Use each service's OAuth client ID + secret.

## Security checklist

- [ ] `curl -sI https://mcp.seehart.com/host/mcp` → 401/403 without Bearer
- [ ] `curl -sI http://mcp.seehart.com/host/mcp` → 301 to HTTPS
- [ ] External ports 8752–8756 closed
- [ ] `deploy-mcp-gateway` fails if secrets missing
- [ ] `/register` disabled (dynamic registration off)

## Ops

```bash
compute status mcp-services
compute ssh mcp-services
sudo systemctl status mcp-host mcp-fish mcp-tesla mcp-bridge mcp-nfnc
sudo tail -f /var/log/mcp-audit/audit.log
```
