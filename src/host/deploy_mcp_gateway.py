"""Deploy MCP gateway to GCP mcp-services VM."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from host.config import load_env

RESOURCE = "mcp-services"
APP_ROOT = "mcp-gateway"
REMOTE_APP_ROOT = "/home/mcp/mcp-gateway"
GATEWAY_SITES_ROOT = "/home/mcp/sites"
GATEWAY_HOST_CONFIG = "/home/mcp/.config/ken/host"
WORKSPACE = Path("/home/ken/ws")

PACKAGE_DIRS: dict[str, Path] = {
    "host": WORKSPACE / "host",
    "cmdline": WORKSPACE / "shared" / "cmdline",
    "ken-mcp": WORKSPACE / "shared" / "mcp",
    "util": WORKSPACE / "util",
    "fish": WORKSPACE / "fish",
    "bridge": WORKSPACE / "bridge",
    "nfnc": WORKSPACE / "nfnc",
}

TESLA_DIR = WORKSPACE / "tesla"

RSYNC_EXCLUDES = [
    ".git",
    ".venv",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
]

SYSTEMD_SERVICES = [
    {
        "name": "mcp-tesla",
        "exec": "/home/mcp/mcp-gateway/.venv/bin/python tesla_mcp.py",
        "workdir": "/home/mcp/mcp-gateway/tesla",
        "env_file": "/home/mcp/.config/tesla/.env",
    },
    {
        "name": "mcp-fish",
        "exec": "/home/mcp/mcp-gateway/.venv/bin/python -m fish.http_server",
        "workdir": "/home/mcp/mcp-gateway",
        "env_file": "/home/mcp/.config/fish/fish.env",
    },
    {
        "name": "mcp-host",
        "exec": "/home/mcp/mcp-gateway/.venv/bin/python -m host.mcp_server",
        "workdir": "/home/mcp/mcp-gateway",
        "env_file": "/home/mcp/.config/ken/host/host.env",
    },
    {
        "name": "mcp-bridge",
        "exec": "/home/mcp/mcp-gateway/.venv/bin/python -m bridge.http_server",
        "workdir": "/home/mcp/mcp-gateway",
        "env_file": "/home/mcp/.config/bridge/bridge.env",
    },
    {
        "name": "mcp-nfnc",
        "exec": "/home/mcp/mcp-gateway/.venv/bin/python -m nfnc.http_server",
        "workdir": "/home/mcp/mcp-gateway",
        "env_file": "/home/mcp/.config/nfnc/nfnc.env",
    },
]


GATEWAY_ENV_FILES = [
    Path.home() / ".config" / "ken" / "host" / "host.env",
    Path.home() / ".config" / "fish" / "fish.env",
    Path.home() / ".config" / "tesla" / ".env",
    Path.home() / ".config" / "nfnc" / "nfnc.env",
    Path.home() / ".config" / "bridge" / "bridge.env",
]


def _load_gateway_env() -> None:
    load_env()
    for path in GATEWAY_ENV_FILES:
        if path.is_file():
            load_dotenv(path, override=False)
    secrets_path = Path.home() / ".config" / "bridge" / "secrets.yaml"
    if secrets_path.is_file():
        data = yaml.safe_load(secrets_path.read_text()) or {}
        for key, value in data.items():
            if isinstance(value, str) and value.strip() and key not in os.environ:
                os.environ[key] = value


def _sync_push(name: str, local: Path, remote_subpath: str) -> int:
    import tempfile

    from compute.providers.gcp import GcpProvider
    from compute.registry import resolve

    resource, provider = resolve(RESOURCE)
    if not isinstance(provider, GcpProvider):
        print(f"{RESOURCE} is not a GCP resource", file=sys.stderr)
        return 1

    project, zone, vm = provider._ssh_base(resource)
    if "/" in remote_subpath:
        remote_parent = f"{REMOTE_APP_ROOT}/{remote_subpath.rsplit('/', 1)[0]}"
    else:
        remote_parent = REMOTE_APP_ROOT
    archive_dir = remote_subpath.rsplit("/", 1)[-1]
    remote_archive = f"/tmp/deploy-{name}.tar.gz"

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        archive = Path(tmp.name)

    tar_argv = ["tar", "czf", str(archive)]
    for pattern in RSYNC_EXCLUDES:
        tar_argv.append(f"--exclude={pattern}")
    if local.name != archive_dir:
        tar_argv.extend(["--transform", f"s/^{local.name}/{archive_dir}/"])
    tar_argv.extend(["-C", str(local.parent), local.name])

    print(f"+ {' '.join(tar_argv)}")
    if subprocess.run(tar_argv, check=False).returncode != 0:
        archive.unlink(missing_ok=True)
        return 1

    scp_argv = [
        "gcloud",
        "compute",
        "scp",
        str(archive),
        f"{vm}:{remote_archive}",
        f"--project={project}",
        f"--zone={zone}",
        "--tunnel-through-iap",
    ]
    print(f"+ {' '.join(scp_argv)}")
    rc = subprocess.run(scp_argv, check=False).returncode
    archive.unlink(missing_ok=True)
    if rc != 0:
        return rc

    extract_cmd = (
        f"sudo mkdir -p {remote_parent} && "
        f"sudo tar xzf {remote_archive} -C {remote_parent} && "
        f"sudo rm -f {remote_archive} && "
        f"sudo chown -R mcp:mcp {REMOTE_APP_ROOT}"
    )
    return _remote_run(extract_cmd)


def _remote_run(command: str) -> int:
    from compute.registry import resolve
    from compute.runner import run_on_resource

    resource, provider = resolve(RESOURCE)
    result = run_on_resource(resource, provider, command)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def _preflight_secrets(*, dry_run: bool) -> list[str]:
    _load_gateway_env()
    checks = [
        ("HOST_MCP_CLIENT_SECRET", os.getenv("HOST_MCP_CLIENT_SECRET", "")),
        ("FISH_MCP_CLIENT_SECRET", os.getenv("FISH_MCP_CLIENT_SECRET", "")),
        ("MCP_CLIENT_SECRET", os.getenv("MCP_CLIENT_SECRET", "")),
        ("NFNC_MCP_CLIENT_SECRET", os.getenv("NFNC_MCP_CLIENT_SECRET", "")),
        ("BRIDGE_MCP_CLIENT_SECRET", os.getenv("BRIDGE_MCP_CLIENT_SECRET", "")),
        ("CURSOR_API_KEY", os.getenv("CURSOR_API_KEY", "")),
    ]
    missing = [name for name, value in checks if not value.strip()]
    if missing and not dry_run:
        print("Missing required secrets for gateway deploy:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
    return missing


def _sync_gateway_host_config() -> int:
    """Sync host MCP registry + manifests for gateway (VM paths, not laptop paths)."""
    import tempfile

    from host.registry import SiteEntry, load_registry

    local_config = Path.home() / ".config" / "ken" / "host"
    entries = load_registry()
    gateway_entries: list[SiteEntry] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for entry in entries:
            repo = Path(entry.repo).expanduser()
            manifest = repo / entry.manifest
            if not manifest.is_file():
                print(f"Skip gateway site {entry.name}: missing {manifest}", file=sys.stderr)
                continue
            site_dir = root / "sites" / entry.name
            site_dir.mkdir(parents=True)
            (site_dir / entry.manifest).write_text(manifest.read_text())
            gateway_entries.append(
                SiteEntry(
                    name=entry.name,
                    repo=f"{GATEWAY_SITES_ROOT}/{entry.name}",
                    manifest=entry.manifest,
                )
            )

        config_dir = root / "config"
        config_dir.mkdir()
        (config_dir / "sites.yaml").write_text(
            yaml.safe_dump(
                {
                    "sites": [
                        {"name": e.name, "repo": e.repo, "manifest": e.manifest}
                        for e in gateway_entries
                    ]
                },
                sort_keys=False,
            )
        )
        for name in ("host.env", "domains.yaml", "deploy_key"):
            local = local_config / name
            if local.is_file():
                dest = config_dir / name
                if name == "deploy_key":
                    dest.write_bytes(local.read_bytes())
                else:
                    dest.write_text(local.read_text())

        if _sync_push("gateway-host-config", root, "gateway-host-config") != 0:
            return 1

    extract = (
        f"sudo mkdir -p {GATEWAY_SITES_ROOT} {GATEWAY_HOST_CONFIG} && "
        f"sudo cp -r {REMOTE_APP_ROOT}/gateway-host-config/sites/. {GATEWAY_SITES_ROOT}/ && "
        f"sudo cp -r {REMOTE_APP_ROOT}/gateway-host-config/config/. {GATEWAY_HOST_CONFIG}/ && "
        f"sudo chown -R mcp:mcp {GATEWAY_SITES_ROOT} {GATEWAY_HOST_CONFIG} && "
        f"sudo chmod 600 {GATEWAY_HOST_CONFIG}/deploy_key 2>/dev/null || true && "
        f"sudo chmod 600 {GATEWAY_HOST_CONFIG}/host.env 2>/dev/null || true"
    )
    return _remote_run(extract)


def _systemd_unit(service: dict) -> str:
    return f"""[Unit]
Description=MCP gateway — {service['name']}
After=network.target

[Service]
Type=simple
User=mcp
Group=mcp
WorkingDirectory={service['workdir']}
Environment=MCP_GATEWAY=1
EnvironmentFile=-{service['env_file']}
ExecStart={service['exec']}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def deploy_mcp_gateway(*, dry_run: bool = False) -> int:
    """Rsync packages + config to mcp-services VM, install venv, restart systemd units."""
    missing = _preflight_secrets(dry_run=dry_run)
    if missing and not dry_run:
        return 1

    template_dir = Path(__file__).resolve().parents[2] / "templates" / "mcp-services"
    if not template_dir.is_dir():
        print(f"Missing templates: {template_dir}", file=sys.stderr)
        return 1

    if dry_run:
        print(f"Dry-run: deploy MCP gateway to {RESOURCE}")
        print(f"  App root: {REMOTE_APP_ROOT}")
        print(f"  Packages: {', '.join(PACKAGE_DIRS)} + tesla")
        if missing:
            print(f"  Missing secrets: {', '.join(missing)}")
        return 1 if missing else 0

    try:
        from compute.providers.base import ResourceState
        from compute.registry import resolve

        resource, provider = resolve(RESOURCE)
        st = provider.status(resource)
        if st.state != ResourceState.RUNNING:
            print(f"Starting {RESOURCE}...")
            provider.start(resource)
    except Exception as exc:
        print(f"Cannot reach {RESOURCE}: {exc}", file=sys.stderr)
        print("Bootstrap the VM — see host/docs/services-mcp.md", file=sys.stderr)
        return 1

    _remote_run(f"sudo mkdir -p {REMOTE_APP_ROOT}/src {REMOTE_APP_ROOT}/tesla && sudo chown -R mcp:mcp {REMOTE_APP_ROOT}")

    for name, local in PACKAGE_DIRS.items():
        if not local.is_dir():
            print(f"Missing: {local}", file=sys.stderr)
            return 1
        if _sync_push(name, local, f"src/{name}") != 0:
            return 1

    if _sync_push("tesla", TESLA_DIR, "tesla") != 0:
        return 1

    if _sync_gateway_host_config() != 0:
        return 1

    requirements = (template_dir / "requirements-deploy.txt").read_text()
    units = "\n".join(
        f"cat > /tmp/{s['name']}.service << 'UNITEOF'\n{_systemd_unit(s)}UNITEOF\n"
        f"sudo mv /tmp/{s['name']}.service /etc/systemd/system/{s['name']}.service\n"
        f"sudo systemctl enable {s['name']}.service\n"
        f"sudo systemctl restart {s['name']}.service\n"
        for s in SYSTEMD_SERVICES
    )

    remote_script = f"""
set -e
APP={REMOTE_APP_ROOT}
sudo mkdir -p "$APP"
sudo chown -R mcp:mcp "$APP"
sudo -u mcp bash <<'MCPEOF'
set -e
APP={REMOTE_APP_ROOT}
cd "$APP"
cat > "$APP/requirements-deploy.txt" << 'REQEOF'
{requirements}REQEOF

if [ ! -d "$APP/.venv" ]; then
  python3 -m venv "$APP/.venv"
fi
"$APP/.venv/bin/pip" install -U pip wheel
"$APP/.venv/bin/pip" install -r "$APP/requirements-deploy.txt"
MCPEOF

sudo mkdir -p /var/log/mcp-audit
sudo chown mcp:mcp /var/log/mcp-audit 2>/dev/null || true

{units}

sudo mkdir -p /var/www/mcp-oauth
sudo cp {REMOTE_APP_ROOT}/src/host/templates/mcp-services/tesla-oauth-callback.html /var/www/mcp-oauth/tesla-callback.html
if [ -f /home/mcp/.config/tesla/com.tesla.3p.public-key.pem ]; then
  sudo cp /home/mcp/.config/tesla/com.tesla.3p.public-key.pem /var/www/mcp-oauth/com.tesla.3p.public-key.pem
fi

sudo cp {REMOTE_APP_ROOT}/src/host/templates/mcp-services/nginx.conf /etc/nginx/sites-available/mcp.seehart.com
sudo ln -sf /etc/nginx/sites-available/mcp.seehart.com /etc/nginx/sites-enabled/mcp.seehart.com
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

if [ -f {REMOTE_APP_ROOT}/src/host/templates/mcp-services/fish-sync.service ]; then
  sudo cp {REMOTE_APP_ROOT}/src/host/templates/mcp-services/fish-sync.service /etc/systemd/system/
  sudo cp {REMOTE_APP_ROOT}/src/host/templates/mcp-services/fish-sync.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  if [ -f /data/fish/fish.db ]; then
    sudo systemctl enable fish-sync.timer
    sudo systemctl start fish-sync.timer 2>/dev/null || true
  fi
fi

echo "OK — gateway deployed"
"""
    rc = _remote_run(remote_script)
    if rc == 0:
        print("\nVerify: sitehost verify-mcp-gateway")
    return rc


def verify_mcp_gateway() -> int:
    """Run security verification checks against live gateway."""
    import urllib.error
    import urllib.request

    checks: list[tuple[str, bool, str]] = []

    def head(url: str) -> int | None:
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception as exc:
            return None

    status = head("https://mcp.seehart.com/host/mcp")
    checks.append(("HTTPS /host/mcp rejects unauthenticated", status in (401, 403), f"got {status}"))

    try:
        req = urllib.request.Request("http://mcp.seehart.com/host/mcp", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            checks.append(("HTTP redirects to HTTPS", resp.geturl().startswith("https://"), resp.geturl()))
    except urllib.error.HTTPError as exc:
        checks.append(("HTTP redirects or refuses", exc.code in (301, 308), str(exc.code)))
    except Exception as exc:
        checks.append(("HTTP redirects or refuses", False, str(exc)))

    failed = 0
    for label, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {label} — {detail}")
        if not ok:
            failed += 1
    return 1 if failed else 0
