# Phase 2 — hosting.com Python MCP experiment

**Status:** blocked — Passenger/WSGI cannot serve FastMCP `streamable-http` (requests hang). See outcome below.

## Hypothesis

hosting.com shared hosting can run a **thin Python app** (FastMCP `streamable-http` + OAuth) at website-level compute. Heavy tools delegate to [`compute`](../../compute/AGENTS.md).

## Target endpoints

| URL | Purpose |
|-----|---------|
| `https://seehart.com/host/mcp` | MCP streamable HTTP |
| `https://seehart.com/host/.well-known/oauth-authorization-server` | OAuth discovery |
| `https://seehart.com/host/authorize` | OAuth authorize |
| `https://seehart.com/host/token` | OAuth token |

Mount confirmed: `PassengerBaseURI "/host"` in `~/seehart.com/host/.htaccess`.

## Deploy steps

1. Complete [Phase 1 static deploy](hosting.md) (clean docroot, no WP `index.php`)
2. cPanel / `cloudlinux-selector create` — Python 3.11, app root `~/host-mcp`, URI `/host`
3. **`sitehost deploy-mcp --manifest /path/to/host.yaml`** (rsyncs template + packages, pip install, restart)
4. Secrets via `~/.config/ken/host/host.env` on server (synced by deploy-mcp)

Manual equivalent:

```bash
set -a && source ~/.config/ken/host/host.env && set +a
sitehost deploy-mcp --manifest /home/ken/ws/seehart/host.yaml
```

**cloudlinux-selector:** use `--domain seehart.com` only (not `--user` + `--domain` together).

```bash
# Local smoke test before upload
cd /home/ken/ws/host
sitehost serve
curl -sI http://127.0.0.1:8754/mcp
```

## Experiment checklist

Record results (2026-06-20):

| Question | Finding |
|----------|---------|
| App type (Passenger, CGI, other) | **Passenger** via CloudLinux selector; LiteSpeed `lswsgi` |
| Process model (long-lived vs per-request) | Passenger prefork; app_status `started` |
| Custom URL paths for OAuth | Mount at `/host`; OAuth paths under `/host/...` |
| Memory / CPU / time limits | Not measured; import ~1.5s |
| HTTPS termination | LiteSpeed at edge; `wsgi.url_scheme` https |
| Outbound SSH (for `host_deploy` rsync) | Not tested yet |
| Outbound HTTPS to GCP/RunPod | Not tested yet |
| `curl -sI https://seehart.com/host/mcp` | **Hangs** (timeout) after import succeeds |
| OAuth discovery JSON valid | **No** — same hang |
| `host_list_sites` tool works | **No** — endpoint unreachable |

### Root cause

FastMCP `streamable-http` is **ASGI** (Starlette). hosting.com exposes **WSGI only** (`lswsgi`). Wrapping with `a2wsgi.ASGIMiddleware` allows import but **requests never complete** (async/event-loop mismatch under Passenger).

Tesla MCP on hosting uses **uvicorn + nginx proxy** on a VPS-style deploy, not shared-hosting Passenger.

## Outcome matrix

| Result | Next step |
|--------|-----------|
| FastMCP + OAuth works | Add Tesla/Fish MCP apps; proceed to Phase 3 (Claude connectors) |
| Python works but OAuth paths broken | Adjust mount or proxy rules; document workaround |
| **Python apps not viable for streamable-http** | **`mcp-services` fallback on GCP** (`compute/resources.yaml`) — **current path** |

## Phase 3 gate

Proceed via GCP gateway — see [`services-mcp.md`](services-mcp.md):

1. Deploy `mcp-services` VM + TLS
2. `sitehost verify-mcp-gateway` passes
3. Register Claude.ai connectors at `https://mcp.seehart.com/...`
