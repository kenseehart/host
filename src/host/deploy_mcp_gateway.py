"""Deploy MCP gateway to GCP mcp-services VM."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from host.config import load_env

RESOURCE = "mcp-services"
APP_ROOT = "mcp-gateway"
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


def _sync_push(name: str, local: Path, remote_subpath: str) -> int:
    from compute.providers.gcp import GcpProvider
    from compute.registry import resolve

    resource, provider = resolve(RESOURCE)
    if not isinstance(provider, GcpProvider):
        print(f"{RESOURCE} is not a GCP resource", file=sys.stderr)
        return 1
    argv = provider.sync_rsync_argv(
        resource,
        direction="push",
        local_path=f"{local}/",
        remote_path=f"~/{APP_ROOT}/{remote_subpath}/",
    )
    for pattern in RSYNC_EXCLUDES:
        argv.extend(["--exclude", pattern])
    print(f"+ {' '.join(argv)}")
    return subprocess.run(argv, check=False).returncode


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
    load_env()
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
        print(f"  App root: ~/{APP_ROOT}")
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

    _remote_run(f"mkdir -p ~/{APP_ROOT}/src ~/{APP_ROOT}/tesla")

    for name, local in PACKAGE_DIRS.items():
        if not local.is_dir():
            print(f"Missing: {local}", file=sys.stderr)
            return 1
        if _sync_push(name, local, f"src/{name}") != 0:
            return 1

    if _sync_push("tesla", TESLA_DIR, "tesla") != 0:
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
APP=~/{APP_ROOT}
cat > $APP/requirements-deploy.txt << 'REQEOF'
{requirements}REQEOF

if [ ! -d $APP/.venv ]; then
  python3 -m venv $APP/.venv
fi
$APP/.venv/bin/pip install -U pip wheel
$APP/.venv/bin/pip install -r $APP/requirements-deploy.txt

sudo mkdir -p /var/log/mcp-audit
sudo chown mcp:mcp /var/log/mcp-audit 2>/dev/null || true

{units}

sudo cp $APP/src/host/templates/mcp-services/nginx.conf /etc/nginx/sites-available/mcp.seehart.com
sudo ln -sf /etc/nginx/sites-available/mcp.seehart.com /etc/nginx/sites-enabled/mcp.seehart.com
sudo nginx -t && sudo systemctl reload nginx
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
