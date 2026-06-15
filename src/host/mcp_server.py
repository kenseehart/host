from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from host.config import (
    load_env,
    mcp_base_url,
    mcp_client_id,
    mcp_client_secret,
    oauth_state_dir,
)
from host.deploy import deploy_site, read_deploy_state
from host.registry import registry_status, resolve_manifest
from host.scaffold import scaffold_template_tree

HOST_INSTRUCTIONS = """
Host MCP — manage static sites on my.hosting.com.

Use host_list_sites to see registered projects, host_status for deploy/git state,
host_deploy to rsync (dry_run=true by default), and host_scaffold for template files.
"""


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_mcp() -> FastMCP:
    load_env()
    auth = None
    secret = mcp_client_secret()
    if secret:
        from ken_mcp import PersonalAuthProvider

        auth = PersonalAuthProvider(
            base_url=mcp_base_url(),
            client_id=mcp_client_id(),
            client_secret=secret,
            client_name="host-mcp-client",
            state_dir=str(oauth_state_dir()),
        )

    mcp = FastMCP("host", instructions=HOST_INSTRUCTIONS, auth=auth)

    @mcp.tool()
    def host_list_sites() -> str:
        """List all sites registered in ~/.config/ken/host/sites.yaml."""
        return _json(registry_status())

    @mcp.tool()
    def host_status(site: str) -> str:
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
        return _json(payload)

    @mcp.tool()
    def host_deploy(site: str, dry_run: bool = True) -> str:
        """Deploy a site via rsync or ftp. Defaults to dry_run=true for safety."""
        m = resolve_manifest(site_name=site)
        code = deploy_site(m, dry_run=dry_run)
        return _json(
            {
                "site": site,
                "dry_run": dry_run,
                "exit_code": code,
                "deploy": read_deploy_state(m.name) if not dry_run else {},
            }
        )

    @mcp.tool()
    def host_scaffold(template: str = "static-site") -> str:
        """Return scaffold template file contents for agents to apply."""
        return _json(scaffold_template_tree(template))

    return mcp


def main() -> None:
    from host.config import mcp_host, mcp_port

    mcp = build_mcp()
    mcp.run(transport="streamable-http", host=mcp_host(), port=mcp_port())


if __name__ == "__main__":
    main()
