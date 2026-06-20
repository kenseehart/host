# MCP services fallback (GCP `mcp-services`)

**Status:** not implemented — only if [hosting-python.md](hosting-python.md) experiment fails.

Do not provision until the Phase 2 outcome matrix in `hosting-python.md` points here.

## When to use

- hosting.com Python apps cannot run FastMCP + OAuth
- Need always-on public HTTPS for Claude.ai connectors

## Sketch

1. Add `mcp-services` to [`compute/resources.yaml`](../../compute/resources.yaml) (GCP e2-small, always-on)
2. DNS `mcp.seehart.com` → VM IP
3. nginx path routing for `/host/`, `/tesla/`, `/fish/`, `/nfnc/`
4. systemd units per MCP service

See workspace plan `seehart_hosting_split` for port allocation.
