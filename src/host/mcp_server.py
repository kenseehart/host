from __future__ import annotations

from cmdline import format_for_agent, parse_columns

from host.config import (
    load_env,
    mcp_base_url,
    mcp_client_id,
    mcp_client_secret,
    oauth_state_dir,
)
from host.deploy import deploy_site, read_deploy_state
from host.inventory import default_columns, inventory_rows
from host.registry import registry_status, resolve_manifest
from host.scaffold import scaffold_template_tree

HOST_INSTRUCTIONS = """
Host MCP — manage static sites on my.hosting.com.

Use host_list_sites to see registered projects, host_inventory for DNS/uptime/renewal,
host_status for deploy/git state, host_deploy to rsync (dry_run=true by default),
and host_scaffold for template files.

Structured tools accept format=text|md|json and optional columns=comma,separated,headers.
"""


def build_mcp(*, require_auth: bool = True):
    from fastmcp import FastMCP
    from ken_mcp import audited_tool, gateway_mode, require_mcp_auth

    load_env()
    auth = None
    if require_auth or gateway_mode():
        auth = require_mcp_auth(
            base_url=mcp_base_url(),
            client_id=mcp_client_id(),
            client_secret=mcp_client_secret(),
            service="host",
            state_dir=str(oauth_state_dir()),
        )
    elif mcp_client_secret():
        from ken_mcp import PersonalAuthProvider

        auth = PersonalAuthProvider(
            base_url=mcp_base_url(),
            client_id=mcp_client_id(),
            client_secret=mcp_client_secret(),
            client_name="host-mcp-client",
            state_dir=str(oauth_state_dir()),
        )

    mcp = FastMCP("host", instructions=HOST_INSTRUCTIONS, auth=auth)

    @mcp.tool()
    @audited_tool("host")
    def host_list_sites(
        format: str = "text",
        columns: str | None = None,
    ) -> str:
        """List sites registered in ~/.config/ken/host/sites.yaml."""
        rows = registry_status()
        return format_for_agent(
            rows,
            format=format,
            title="Registered sites",
            columns=parse_columns(columns),
        )

    @mcp.tool()
    @audited_tool("host")
    def host_inventory(
        owner: str = "ken",
        hosting: str | None = None,
        format: str = "text",
        columns: str | None = None,
        probe: bool = True,
    ) -> str:
        """Domain inventory: DNS, HTTP up/down, renewal, hosting metadata."""
        rows = inventory_rows(owner=owner, hosting=hosting, probe=probe)
        col_list = parse_columns(columns) or default_columns()
        return format_for_agent(
            rows,
            format=format,
            title=f"Domain inventory ({owner})",
            columns=col_list,
        )

    @mcp.tool()
    @audited_tool("host")
    def host_status(
        site: str,
        format: str = "text",
        columns: str | None = None,
    ) -> str:
        """Deploy and git status for a registered site."""
        from host.config import git_status

        m = resolve_manifest(site_name=site)
        payload = {
            "name": m.name,
            "domain": m.domain,
            "local_static": str(m.local_static_path),
            "remote": m.static.remote,
            "transport": m.static.transport,
            "deploy": read_deploy_state(m.name),
            "git": git_status(m.repo_root or m.local_static_path.parent),
        }
        return format_for_agent(payload, format=format, title=f"Site: {site}", columns=parse_columns(columns))

    @mcp.tool()
    @audited_tool("host")
    def host_deploy(site: str, dry_run: bool = True, format: str = "json") -> str:
        """Deploy a site via rsync or ftp. Defaults to dry_run=true for safety."""
        m = resolve_manifest(site_name=site)
        code = deploy_site(m, dry_run=dry_run)
        payload = {
            "site": site,
            "dry_run": dry_run,
            "exit_code": code,
            "deploy": read_deploy_state(m.name) if not dry_run else {},
        }
        return format_for_agent(payload, format=format, title=f"Deploy: {site}")

    @mcp.tool()
    @audited_tool("host")
    def host_scaffold(template: str = "static-site", format: str = "json") -> str:
        """Return scaffold template file contents for agents to apply."""
        return format_for_agent(
            scaffold_template_tree(template),
            format=format,
            title=f"Scaffold: {template}",
        )

    return mcp


def main() -> None:
    from host.config import mcp_host, mcp_port

    mcp = build_mcp(require_auth=True)
    mcp.run(transport="streamable-http", host=mcp_host(), port=mcp_port())


if __name__ == "__main__":
    main()
