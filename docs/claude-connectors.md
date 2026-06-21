# Claude.ai MCP connector registration

Manual step after gateway deploy and `sitehost verify-mcp-gateway` passes.

## Where to go

**[https://claude.ai/customize/connectors](https://claude.ai/customize/connectors)**

(Legacy URL `claude.ai/settings/connectors` may still work for remove/edit.)

Click **Add custom connector** → enter MCP URL → expand **Advanced settings** for OAuth credentials.

## Prerequisites

- Gateway live at `https://mcp.seehart.com`
- OAuth client ID + secret per service (in `~/.config/` env files on laptop)
- Claude Pro/Team account with custom connector support

**Required:** enter Client ID + Client Secret in Advanced settings. Dynamic registration (`/register`) is disabled on the gateway — leaving OAuth blank will fail.

## Connectors

| Display name | MCP URL | Client ID env | Client secret env |
|--------------|---------|---------------|-------------------|
| Ken Host | `https://mcp.seehart.com/host/mcp` | `HOST_MCP_CLIENT_ID` | `HOST_MCP_CLIENT_SECRET` |
| Ken Tesla | `https://mcp.seehart.com/tesla/mcp` | `MCP_CLIENT_ID` | `MCP_CLIENT_SECRET` |
| Ken Fish | `https://mcp.seehart.com/fish/mcp` | `FISH_MCP_CLIENT_ID` | `FISH_MCP_CLIENT_SECRET` |
| Ken NFNC | `https://mcp.seehart.com/nfnc/mcp` | `NFNC_MCP_CLIENT_ID` | `NFNC_MCP_CLIENT_SECRET` |
| Ken Agent | `https://mcp.seehart.com/agent/mcp` | `BRIDGE_MCP_CLIENT_ID` | `BRIDGE_MCP_CLIENT_SECRET` |

Client IDs are usually `host-mcp`, `tesla-mcp`, `fish-mcp`, `nfnc-mcp`, `bridge-mcp`.

After **Add**, click **Connect** and complete OAuth (browser may redirect to `mcp.seehart.com` briefly).

## Phone E2E test

1. **Host:** “List my registered sites” → should call `host_list_sites`
2. **Bridge:** “Run a cloud agent on kenseehart/host to show git status” → `agent_run` + poll `agent_status`

## Removing a broken connector

Claude’s UI often has **no delete** for failed custom connectors (known gap). Options:

1. **Legacy settings page:** [claude.ai/settings/connectors](https://claude.ai/settings/connectors) — may show Remove / ⋮ menu
2. **Re-connect without delete:** if OAuth is fixed, **Connect** again on the same entry — usually enough; delete only needed to change URL or credentials
3. **API delete** (last resort): DevTools → Network → `mcp/v2/bootstrap` SSE → copy connector `uuid`; then in browser console on claude.ai:
   ```js
   await fetch(`/api/organizations/${ORG_UUID}/mcp/remote_servers/${SERVER_UUID}`, {
     method: 'DELETE', credentials: 'include',
   });
   ```
   (`ORG_UUID` from `app_start` request URL in Network tab.)

## Troubleshooting

- **404 on Connect (nginx):** gateway nginx must route root OAuth paths (`/.well-known/oauth-protected-resource/…`, `/authorize`). Fixed in `host/templates/mcp-services/nginx.conf` — redeploy with `sitehost deploy-mcp-gateway` if missing.
- **OAuth fails / wrong client:** verify Advanced settings match VM env; IDs must be `host-mcp` etc., not random UUIDs (UUID = OAuth fields were left blank).
- **401 on tools:** re-authorize connector; check secret matches VM env.
- **Tools timeout on bridge:** use `agent_status` / `agent_result` — cloud agents run async.
