"""Host CLI — decorator-driven commands via cmdline."""

from __future__ import annotations

import sys
from pathlib import Path

from cmdline import cmd, create_parser, emit_output, optarg, parse_columns, run_cli, cmds

from host.config import load_env
from host.deploy import deploy_site, read_deploy_state, validate_manifest
from host.manifest import find_manifest, load_manifest
from host.registry import register_site, registry_status, resolve_manifest
from host.scaffold import scaffold_static_site, scaffold_template_tree


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
    allow_public_html: bool = optarg(
        False,
        long_flag="--allow-public-html",
        action="store_true",
        help="Allow deploy to ~/public_html (primary docroot — confirm in cPanel first)",
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

    issues = validate_manifest(m, allow_public_html=allow_public_html)
    if issues:
        for issue in issues:
            print(f"validate: {issue}", file=sys.stderr)
        return 1

    print(f"Deploying {m.name} ({m.domain}) via {m.static.transport}...")
    print(f"  local:  {m.local_static_path}")
    print(f"  remote: {m.static.remote}")
    return deploy_site(m, dry_run=dry_run, allow_public_html=allow_public_html)


@cmd
def validate(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    manifest: str | None = optarg(None, long_flag="--manifest", help="Path to host.yaml"),
    allow_public_html: bool = optarg(
        False,
        long_flag="--allow-public-html",
        action="store_true",
        help="Allow validate when static.remote is ~/public_html",
    ),
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

    issues = validate_manifest(m, allow_public_html=allow_public_html)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print(f"OK: {m.name} -> {m.local_static_path}")
    return 0


@cmd(output=True)
def sites(*, json_output: bool = False, md_output: bool = False) -> int:
    """List sites in the host registry."""
    rows = registry_status()
    if not rows and not json_output:
        print("No sites registered. Run: host mkweb <name> --domain example.com")
        return 0
    emit_output(rows, json_output=json_output, md=md_output, title="Registered sites")
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


@cmd(output=True)
def status(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    *,
    json_output: bool = False,
    md_output: bool = False,
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
    emit_output(payload, json_output=json_output, md=md_output, title=f"Site: {m.name}")
    return 0


@cmd
def setup_deploy(
    repo: str = optarg(
        "kenseehart/seehart",
        long_flag="--repo",
        help="GitHub repo for Actions secrets",
    ),
    ssh_user: str | None = optarg(
        None, long_flag="--ssh-user", help="cPanel SSH username"
    ),
    ssh_host: str = optarg("seehart.com", long_flag="--ssh-host", help="SSH hostname"),
    apply_gh: bool = optarg(
        False,
        long_flag="--apply-gh",
        action="store_true",
        help="Run gh secret set (needs admin:repo)",
    ),
) -> int:
    """Generate deploy key + host.env; print hosting.com setup steps."""
    from host.setup_deploy import apply_github_secrets, print_setup_instructions

    print_setup_instructions(repo=repo, ssh_user=ssh_user, ssh_host=ssh_host)
    if apply_gh:
        if not ssh_user:
            print("--apply-gh requires --ssh-user", file=sys.stderr)
            return 1
        return apply_github_secrets(repo=repo, ssh_user=ssh_user, ssh_host=ssh_host)
    return 0


@cmd
def remote_prepare(
    site: str | None = optarg(None, long_flag="--site", help="Registered site name"),
    manifest: str | None = optarg(None, long_flag="--manifest", help="Path to host.yaml"),
    no_backup: bool = optarg(
        False,
        long_flag="--no-backup",
        action="store_true",
        help="Skip tar backup of docroot",
    ),
    allow_public_html: bool = optarg(
        False,
        long_flag="--allow-public-html",
        action="store_true",
        help="Allow prepare on ~/public_html (primary docroot — confirm in cPanel first)",
    ),
) -> int:
    """Backup docroot and remove WordPress files before first static deploy."""
    from host.deploy import remote_prepare_wordpress

    load_env()
    try:
        if manifest:
            m = load_manifest(manifest)
        else:
            m = resolve_manifest(site_name=site)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    issues = validate_manifest(m, allow_public_html=allow_public_html)
    if issues:
        for issue in issues:
            print(f"validate: {issue}", file=sys.stderr)
        return 1

    print(f"Preparing {m.domain} docroot at {m.static.remote}...")
    return remote_prepare_wordpress(m, backup=not no_backup, allow_public_html=allow_public_html)


@cmd(output=True)
def inventory(
    owner: str = optarg("ken", long_flag="--owner", help="Filter by owner (ken, jeff, other)"),
    hosting: str | None = optarg(None, long_flag="--hosting", help="Filter by hosting provider"),
    columns: str | None = optarg(
        None,
        long_flag="--columns",
        help="Comma-separated columns (default: inventory preset)",
    ),
    no_probe: bool = optarg(
        False,
        long_flag="--no-probe",
        action="store_true",
        help="Skip live DNS/HTTP/WHOIS checks",
    ),
    *,
    json_output: bool = False,
    md_output: bool = False,
) -> int:
    """Domain inventory: DNS, uptime, renewal, hosting metadata."""
    from host.inventory import default_columns, inventory_rows

    rows = inventory_rows(owner=owner, hosting=hosting, probe=not no_probe)
    if not rows:
        print(
            "No domains found. Copy host/templates/domains.yaml.example to "
            "~/.config/ken/host/domains.yaml",
            file=sys.stderr,
        )
        return 1
    col_list = parse_columns(columns) or default_columns()
    emit_output(
        rows,
        json_output=json_output,
        md=md_output,
        title=f"Domain inventory ({owner})",
        columns=col_list,
    )
    return 0


@cmd
def deploy_mcp(
    manifest: str | None = optarg(None, long_flag="--manifest", help="Path to host.yaml"),
    domain: str | None = optarg(None, long_flag="--domain", help="Python app domain (default: manifest domain)"),
    dry_run: bool = optarg(
        False, long_flag="--dry-run", action="store_true", help="Print plan only"
    ),
) -> int:
    """Deploy Host MCP Python app to hosting.com (Phase 2)."""
    from host.deploy_mcp import deploy_mcp as run_deploy_mcp
    from host.manifest import find_manifest, load_manifest

    if manifest:
        m = load_manifest(Path(manifest))
    else:
        found = find_manifest()
        if found is None:
            print("No host.yaml found. Pass --manifest.", file=sys.stderr)
            return 1
        m = load_manifest(found)
    return run_deploy_mcp(m, dry_run=dry_run, domain=domain)


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
