# Next session prompt — platform hosting rollout

Copy everything below the line into a new Cursor chat to continue.

---

Continue Ken workspace platform hosting rollout.

## Decisions (locked in)

- **MCP gateway:** GCP `mcp-services` VM at `https://mcp.seehart.com` (Phase 2 hosting.com Passenger blocked)
- **Two platforms:** `host` (A2 static) + `compute` (GCP/RunPod). MCP HTTP on GCP e2-small always-on.
- **Claude.ai:** five HTTPS OAuth connectors (host, tesla, fish, nfnc, bridge)
- **Cursor tunnel:** `bridge` MCP → Cursor cloud agents via `cursor-sdk`
- **Standard registrar:** Cloudflare — see `host/docs/domains-and-dns.md`

## Completed

| Item | Status |
|------|--------|
| Phase 1 seehart.com static | ✅ https://seehart.com |
| Docroot guard (`~/public_html`) | ✅ |
| `cmdline.progress` pushed | ✅ shared repo |
| MCP gateway code + deploy CLI | ✅ `sitehost deploy-mcp-gateway` |
| Security hardening (fail-closed, no /register) | ✅ ken_mcp |
| `bridge/` Cursor tunnel MCP | ✅ |
| nfnc HTTP MCP | ✅ |

## Do next (priority order)

### 1. Bootstrap mcp-services VM (if not done)
- Follow [`host/docs/mcp-gateway-rollout-prompt.md`](mcp-gateway-rollout-prompt.md) — **one step at a time**
- `compute up mcp-services`

### 2. Deploy gateway
```bash
sitehost deploy-mcp-gateway --dry-run
sitehost deploy-mcp-gateway
sitehost verify-mcp-gateway
```

### 3. Register Claude.ai connectors
- Five URLs in `services-mcp.md` — manual in Claude settings

### 4. Decommission seehart.com `/host` Passenger app (non-functional)

### 5. Phase 4 static sites + Cloudflare registrar

## Key paths

| Path | Purpose |
|------|---------|
| `host/docs/services-mcp.md` | Gateway runbook |
| `bridge/AGENTS.md` | Cursor tunnel MCP |
| `compute/resources.yaml` | `mcp-services` resource |
| `~/.config/ken/host/host.env` | Deploy + MCP secrets |
