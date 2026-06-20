# Phase 2 — hosting.com Python MCP experiment

**Status:** in progress — fill in findings below after deploying to seehart.com.

## Hypothesis

hosting.com shared hosting can run a **thin Python app** (FastMCP `streamable-http` + OAuth) at website-level compute. Heavy tools delegate to [`compute`](../../compute/AGENTS.md).

## Target endpoints

| URL | Purpose |
|-----|---------|
| `https://seehart.com/host/mcp` | MCP streamable HTTP |
| `https://seehart.com/host/.well-known/oauth-authorization-server` | OAuth discovery |
| `https://seehart.com/host/authorize` | OAuth authorize |
| `https://seehart.com/host/token` | OAuth token |

Exact paths depend on cPanel app URL mount — record actual URLs here.

## Deploy steps

1. Complete [Phase 1 static deploy](hosting.md) (clean docroot, no WP `index.php`)
2. cPanel → **Setup Python App**
   - Python 3.10+
   - App root: e.g. `~/apps/host-mcp`
   - App URL: `/host` (or subdomain — record choice)
3. Copy [`templates/python-app/`](../templates/python-app/) to app root
4. In app virtualenv: install `requirements.txt` + editable `host`, `ken-mcp`, `cmdline`, `util`
5. Set env vars from `~/.config/ken/host/host.env` in cPanel app config
6. Restart app

```bash
# Local smoke test before upload
cd /home/ken/ws/host
sitehost serve
curl -sI http://127.0.0.1:8754/mcp
```

## Experiment checklist

Record results:

| Question | Finding |
|----------|---------|
| App type (Passenger, CGI, other) | _TBD_ |
| Process model (long-lived vs per-request) | _TBD_ |
| Custom URL paths for OAuth | _TBD_ |
| Memory / CPU / time limits | _TBD_ |
| HTTPS termination | _TBD_ |
| Outbound SSH (for `host_deploy` rsync) | _TBD_ |
| Outbound HTTPS to GCP/RunPod | _TBD_ |
| `curl -sI https://seehart.com/host/mcp` | _TBD_ |
| OAuth discovery JSON valid | _TBD_ |
| `host_list_sites` tool works | _TBD_ |

## Thin-orchestrator validation

| Tool | Expected behavior |
|------|-------------------|
| `host_list_sites` | Read registry — no compute |
| `host_status` | Read deploy state + git — no compute |
| `host_deploy` | Rsync via SSH — website-level I/O |
| `host_scaffold` | Return templates — no compute |

Future fish/daime MCP tools that need GPU must call `compute up` + `compute run`, not run locally on hosting.com.

## Outcome matrix

| Result | Next step |
|--------|-----------|
| FastMCP + OAuth works | Add Tesla/Fish MCP apps; proceed to Phase 3 (Claude connectors) |
| Python works but OAuth paths broken | Adjust mount or proxy rules; document workaround |
| Python apps not viable | `mcp-services` fallback on GCP (`compute/resources.yaml`) |

## Phase 3 gate

Do **not** register Claude.ai connectors until this doc has:

1. Confirmed public HTTPS MCP URL
2. Successful OAuth end-to-end test
3. Valid `tools/list` response
