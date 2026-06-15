"""Host CLI — decorator-driven commands via cmdline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cmdline import cmd, create_parser, optarg, run_cli, cmds

from host.config import load_env
from host.deploy import deploy_site, read_deploy_state, validate_manifest
from host.manifest import find_manifest, load_manifest
from host.registry import register_site, registry_status, resolve_manifest
from host.scaffold import scaffold_static_site, scaffold_template_tree


def _flag(value: object) -> bool:
    """Coerce cmdline optarg when subparser did not bind optional flags."""
    return value is True if isinstance(value, bool) else False


@cmd
def mkweb(
    name: str,
    domain: str = optarg(..., long_flag="--domain", help="Site domain (e.g. seehart.com)"),
    remote: str | None = optarg(
        None, long_flag="--remote", help="Remote docroot path on hosting"
    ),
    register: bool = optarg(
        True,
        long_flag="--register/--no-register",
        help="Add site to ~/.config/ken/host/sites.yaml",
    ),
) -> int:
    """Scaffold site/, host.yaml, and deploy workflow in the current directory."""
    cwd = Path.cwd()
    try:
        scaffold_static_site(name, domain, target_dir=cwd, remote_path=remote)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    if register:
        register_site(name.lower().replace(" ", "-"), str(cwd))
    print(f"Scaffolded static site '{name}' at {cwd}")
    print(f"  site/       — static HTML")
    print(f"  host.yaml   — deploy manifest")
    print(f"  .github/workflows/deploy-*.yml")
    return 0


@cmd
def deploy(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    dry_run: bool = optarg(
        False, long_flag="--dry-run", action="store_true", help="Preview rsync only"
    ),
    manifest: str | None = optarg(
        None, long_flag="--manifest", help="Path to host.yaml (default: search cwd)"
    ),
) -> int:
    """Deploy static site per host.yaml (rsync or ftp)."""
    load_env()
    try:
        if manifest:
            m = load_manifest(manifest)
        else:
            m = resolve_manifest(site_name=site)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    issues = validate_manifest(m)
    if issues:
        for issue in issues:
            print(f"validate: {issue}", file=sys.stderr)
        return 1

    print(f"Deploying {m.name} ({m.domain}) via {m.static.transport}...")
    print(f"  local:  {m.local_static_path}")
    print(f"  remote: {m.static.remote}")
    return deploy_site(m, dry_run=dry_run)


@cmd
def validate(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    manifest: str | None = optarg(None, long_flag="--manifest", help="Path to host.yaml"),
) -> int:
    """Validate host.yaml and local static paths."""
    try:
        if manifest:
            m = load_manifest(manifest)
        else:
            m = resolve_manifest(site_name=site)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    issues = validate_manifest(m)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print(f"OK: {m.name} -> {m.local_static_path}")
    return 0


@cmd
def sites(
    json_output: bool = optarg(False, long_flag="--json", action="store_true", help="JSON output"),
) -> int:
    """List sites in the host registry."""
    rows = registry_status()
    if _flag(json_output):
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("No sites registered. Run: host mkweb <name> --domain example.com")
        return 0
    for row in rows:
        status = "OK" if row.get("manifest_exists") else "missing manifest"
        print(f"{row['name']}: {row.get('domain', '?')} [{status}]")
        print(f"  repo: {row['repo']}")
    return 0


@cmd
def register(
    name: str,
    repo: str | None = optarg(None, long_flag="--repo", help="Repo path (default: cwd)"),
) -> int:
    """Register current or given repo in the host sites registry."""
    repo_path = Path(repo or Path.cwd()).resolve()
    manifest = repo_path / "host.yaml"
    if not manifest.is_file():
        print(f"No host.yaml in {repo_path}", file=sys.stderr)
        return 1
    register_site(name, str(repo_path))
    print(f"Registered site '{name}' -> {repo_path}")
    return 0


@cmd
def status(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    json_output: bool = optarg(False, long_flag="--json", action="store_true", help="JSON output"),
) -> int:
    """Show deploy and git status for a site."""
    from host.config import git_status

    try:
        m = resolve_manifest(site_name=site)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    deploy_state = read_deploy_state(m.name)
    git = git_status(m.repo_root or Path.cwd())
    payload = {
        "name": m.name,
        "domain": m.domain,
        "transport": m.static.transport,
        "local_static": str(m.local_static_path),
        "remote": m.static.remote,
        "deploy": deploy_state,
        "git": git,
    }
    if _flag(json_output):
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Site: {m.name} ({m.domain})")
    print(f"  static: {m.local_static_path}")
    print(f"  remote: {m.static.remote} ({m.static.transport})")
    if deploy_state:
        print(f"  last deploy: {deploy_state.get('updated_at', 'unknown')}")
        print(f"  last ok: {deploy_state.get('last_deploy_ok')}")
    if git.get("is_git"):
        print(f"  branch: {git.get('branch')} dirty={git.get('dirty')}")
    return 0


@cmd
def serve() -> int:
    """Run Host MCP HTTP server (Claude.ai connector)."""
    from host.mcp_server import main as mcp_main

    mcp_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser(
        cmds(sys.modules[__name__]),
        prog="host",
        description="Host — static site scaffold, deploy, and site registry",
    )
    return run_cli(parser, argv)


if __name__ == "__main__":
    raise SystemExit(main())
