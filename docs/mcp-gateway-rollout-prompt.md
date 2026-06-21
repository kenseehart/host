# MCP gateway rollout — step-by-step prompts

Copy **one step at a time** into a new Cursor chat. Do not proceed to the next step until the **Done when** checklist passes.

Reference: [`services-mcp.md`](services-mcp.md), [`claude-connectors.md`](claude-connectors.md)

---

## Step 1 — Bootstrap GCP VM

```
Continue MCP gateway rollout — Step 1 only: bootstrap the mcp-services GCP VM.

Context:
- Code is merged (host deploy-mcp-gateway, compute/resources.yaml mcp-services)
- compute manages start/stop of an EXISTING GCE VM — it does not create VMs
- Runbook: host/docs/services-mcp.md

Do this step only:
1. Confirm gcloud is installed and authenticated (same GCP project as daime-gpu)
2. Create VM mcp-services (e2-small, Ubuntu 22.04, tag mcp-services) in us-central1-a
3. Create firewall rules: allow tcp:443 from 0.0.0.0/0; allow tcp:22 from IAP 35.235.240.0/20
4. Reserve or note the VM external IP
5. SSH via IAP: compute ssh mcp-services (or gcloud compute ssh)
6. On VM: install nginx, certbot, python3-venv, git; create user mcp; mkdir /var/log/mcp-audit owned by mcp

Done when:
- compute status mcp-services shows RUNNING
- compute ssh mcp-services works
- nginx --version and python3 --version succeed on VM

Do NOT do DNS, secrets, or deploy yet.
```

---

## Step 2 — DNS and TLS

```
Continue MCP gateway rollout — Step 2 only: DNS and TLS for mcp.seehart.com.

Prerequisite: Step 1 complete (VM running, external IP known).

Do this step only:
1. Add DNS A record: mcp.seehart.com → VM external IP (Cloudflare or A2 DNS)
2. Wait for propagation; confirm: dig +short mcp.seehart.com
3. On VM: sudo certbot --nginx -d mcp.seehart.com
4. Confirm port 80 redirects to 443: curl -sI http://mcp.seehart.com/ | head -5

Done when:
- dig mcp.seehart.com returns the VM IP
- curl -sI https://mcp.seehart.com/ returns 200 or nginx default (not connection refused)
- HTTP redirects to HTTPS

Do NOT deploy MCP services yet (nginx site config comes with deploy).
```

---

## Step 3 — Secrets on laptop and VM

```
Continue MCP gateway rollout — Step 3 only: configure and sync secrets.

Prerequisite: Steps 1–2 complete.

Generate strong secrets (openssl rand -hex 32) for each service. Set on LAPTOP first:

~/.config/ken/host/host.env:
  HOST_MCP_BASE_URL=https://mcp.seehart.com/host
  HOST_MCP_CLIENT_ID=host-mcp
  HOST_MCP_CLIENT_SECRET=<secret>
  HOST_MCP_HOST=127.0.0.1
  HOST_MCP_PORT=8754
  MCP_GATEWAY=1

~/.config/fish/fish.env:
  FISH_MCP_BASE_URL=https://mcp.seehart.com/fish
  FISH_MCP_CLIENT_ID=fish-mcp
  FISH_MCP_CLIENT_SECRET=<secret>

~/.config/tesla/.env (or existing tesla env):
  MCP_BASE_URL=https://mcp.seehart.com/tesla
  MCP_CLIENT_ID=tesla-mcp
  MCP_CLIENT_SECRET=<secret>

~/.config/nfnc/nfnc.env:
  NFNC_MCP_BASE_URL=https://mcp.seehart.com/nfnc
  NFNC_MCP_CLIENT_ID=nfnc-mcp
  NFNC_MCP_CLIENT_SECRET=<secret>

~/.config/bridge/bridge.env:
  BRIDGE_MCP_BASE_URL=https://mcp.seehart.com/agent
  BRIDGE_MCP_CLIENT_ID=bridge-mcp
  BRIDGE_MCP_CLIENT_SECRET=<secret>

~/.config/bridge/secrets.yaml:
  CURSOR_API_KEY: <from Cursor dashboard>

~/.config/bridge/repos.yaml — repo allowlist (see bridge/AGENTS.md)

Also ensure on VM (as user mcp): host deploy key, fish DB, tesla tokens, nfnc Google creds — chmod 600.

Do this step only: create/fill all env files locally; rsync or scp to VM under /home/mcp/.config/...

Done when:
- sitehost deploy-mcp-gateway --dry-run exits 0 (no missing secrets)
- All env files exist on VM with mode 600

Do NOT run full deploy yet.
```

---

## Step 4 — Deploy gateway

```
Continue MCP gateway rollout — Step 4 only: deploy all five MCP services.

Prerequisite: Steps 1–3 complete.

Do this step only:
1. global_setup   # refresh local packages
2. compute up mcp-services
3. sitehost deploy-mcp-gateway --dry-run   # must pass
4. sitehost deploy-mcp-gateway
5. On VM verify systemd: sudo systemctl status mcp-host mcp-fish mcp-tesla mcp-bridge mcp-nfnc
6. Smoke curl (may 401 without token — that is OK):
   curl -sI https://mcp.seehart.com/host/mcp
   curl -s https://mcp.seehart.com/host/.well-known/oauth-authorization-server

Done when:
- All five systemd units active (running)
- OAuth discovery JSON returns for /host/ (not 502/504)
- curl without Authorization returns 401/403 on /host/mcp

Do NOT register Claude connectors yet.
```

---

## Step 5 — Security verification

```
Continue MCP gateway rollout — Step 5 only: run security verification checklist.

Prerequisite: Step 4 complete (gateway deployed).

Do this step only:
1. sitehost verify-mcp-gateway
2. Manually confirm:
   - curl -sI https://mcp.seehart.com/host/mcp → 401 or 403 (no Bearer)
   - curl -sI http://mcp.seehart.com/host/mcp → 301/308 to https
   - External nmap on ports 8752–8756 → filtered (optional)
   - POST https://mcp.seehart.com/host/register → error/disabled

Done when:
- sitehost verify-mcp-gateway exits 0
- All checklist items in host/docs/services-mcp.md Security section pass

Do NOT register Claude connectors until this passes.
```

---

## Step 6 — Register Claude.ai connectors

```
Continue MCP gateway rollout — Step 6 only: register Claude.ai MCP connectors.

Prerequisite: Step 5 security verification passed.

Manual in Claude.ai → Settings → Connectors. Register five connectors (see host/docs/claude-connectors.md):

| Name       | URL                                      |
|------------|------------------------------------------|
| Ken Host   | https://mcp.seehart.com/host/mcp         |
| Ken Tesla  | https://mcp.seehart.com/tesla/mcp        |
| Ken Fish   | https://mcp.seehart.com/fish/mcp         |
| Ken NFNC   | https://mcp.seehart.com/nfnc/mcp         |
| Ken Agent  | https://mcp.seehart.com/agent/mcp        |

Use each service's CLIENT_ID + CLIENT_SECRET from Step 3. Complete OAuth for each.

Phone E2E test:
1. Host: "List my registered sites" → host_list_sites
2. Bridge: "Run agent on kenseehart/host to show git status" → agent_run, poll agent_status

Done when:
- All five connectors show connected in Claude.ai
- Host and Bridge tools work from phone

Do NOT tear down seehart Passenger until connectors work.
```

---

## Step 7 — Decommission seehart.com /host Passenger app

```
Continue MCP gateway rollout — Step 7 only: remove non-functional Passenger app on seehart.com.

Prerequisite: Step 6 complete (Claude connectors working via mcp.seehart.com).

The old Phase 2 experiment mounted host-mcp at seehart.com/host via Passenger — it never worked (WSGI/ASGI hang). Safe to remove now that gateway is live.

Do this step only:
1. SSH zillions@seehart.com
2. Remove or disable cloudlinux-selector Python app host-mcp at /host
3. Remove ~/seehart.com/host/.htaccess Passenger mount if no longer needed
4. Optionally remove ~/host-mcp app root (backup first)
5. Confirm https://seehart.com still serves static site (unchanged)
6. Confirm https://mcp.seehart.com/host/mcp still works (gateway)

Done when:
- seehart.com static site still live
- No Passenger app at /host
- MCP access only via mcp.seehart.com

Rollout complete.
```
