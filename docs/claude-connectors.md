# Claude.ai MCP connector registration

Manual step after gateway deploy and `sitehost verify-mcp-gateway` passes.

## Prerequisites

- Gateway live at `https://mcp.seehart.com`
- OAuth client ID + secret per service (in VM env files)
- Claude Pro/Team account with custom connector support

## Connectors

In Claude.ai → Settings → Connectors → Add custom connector:

| Display name | MCP URL | Client ID env | Client secret env |
|--------------|---------|---------------|-------------------|
| Ken Host | `https://mcp.seehart.com/host/mcp` | `HOST_MCP_CLIENT_ID` | `HOST_MCP_CLIENT_SECRET` |
| Ken Tesla | `https://mcp.seehart.com/tesla/mcp` | `MCP_CLIENT_ID` | `MCP_CLIENT_SECRET` |
| Ken Fish | `https://mcp.seehart.com/fish/mcp` | `FISH_MCP_CLIENT_ID` | `FISH_MCP_CLIENT_SECRET` |
| Ken NFNC | `https://mcp.seehart.com/nfnc/mcp` | `NFNC_MCP_CLIENT_ID` | `NFNC_MCP_CLIENT_SECRET` |
| Ken Agent | `https://mcp.seehart.com/agent/mcp` | `BRIDGE_MCP_CLIENT_ID` | `BRIDGE_MCP_CLIENT_SECRET` |

Complete OAuth for each connector when prompted.

## Phone E2E test

1. **Host:** “List my registered sites” → should call `host_list_sites`
2. **Bridge:** “Run a cloud agent on kenseehart/host to show git status” → `agent_run` + poll `agent_status`

## Troubleshooting

- **OAuth fails:** verify `*_MCP_BASE_URL` matches public path (includes `/host`, `/agent`, etc.)
- **Tools timeout on bridge:** use `agent_status` / `agent_result` — cloud agents run async
- **401 on tools:** re-authorize connector; check secret matches VM env
