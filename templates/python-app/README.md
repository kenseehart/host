# Host MCP on hosting.com (thin Python app)

Copy this tree into your cPanel **Setup Python App** application root (e.g.
`~/apps/host-mcp/`). Point the app URL to `/host` or mount under `seehart.com/host`.

## Files

| File | Purpose |
|------|---------|
| `passenger_wsgi.py` | Passenger / LiteSpeed WSGI entry |
| `requirements.txt` | Pip deps for the app venv |
| `.env` | `HOST_MCP_*` secrets (create on server, mode 600) |

## Server `.env` example

```env
HOST_MCP_BASE_URL=https://seehart.com/host
HOST_MCP_CLIENT_ID=host-mcp
HOST_MCP_CLIENT_SECRET=<from sitehost setup-deploy>
HOST_SSH_USER=<cpanel-user>
HOST_SSH_HOST=seehart.com
```

OAuth state persists under `~/.config/ken/host/oauth-state` on the server.

## cPanel steps (record findings in docs/hosting-python.md)

1. **Setup Python App** — Python 3.10+, app root, app URL `/host`
2. `pip install -r requirements.txt` plus editable `host` and `ken-mcp` packages
3. Copy `passenger_wsgi.py` to app root
4. Set environment variables in cPanel app config
5. Restart app

## Verify

```bash
curl -sI https://seehart.com/host/mcp
curl -s https://seehart.com/.well-known/oauth-authorization-server
```

## Thin orchestrator

Host MCP tools must stay lightweight. Heavy work delegates to `compute`:

- `host_deploy` — rsync only
- Future fish/daime tools — `compute run <resource> '...'`, not local GPU
