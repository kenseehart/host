from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from host.manifest import SiteManifest, default_ssh_host, default_ssh_user

DEPLOY_STATE_DIR = Path.home() / ".config" / "ken" / "host" / "deploy-state"


def _state_file(site_name: str) -> Path:
    DEPLOY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return DEPLOY_STATE_DIR / f"{site_name}.json"


def read_deploy_state(site_name: str) -> dict:
    f = _state_file(site_name)
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def write_deploy_state(site_name: str, **fields) -> None:
    state = read_deploy_state(site_name)
    state.update(fields)
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _state_file(site_name).write_text(json.dumps(state, indent=2))


def _ssh_target(manifest: SiteManifest) -> str:
    host = manifest.static.ssh_host or default_ssh_host(manifest.domain)
    user = manifest.static.ssh_user or default_ssh_user()
    if not user:
        raise ValueError(
            "SSH user not configured. Set static.ssh_user in host.yaml or HOST_SSH_USER."
        )
    return f"{user}@{host}"


def _ssh_command() -> str:
    identity = os.environ.get("HOST_SSH_IDENTITY_FILE", "").strip()
    if identity:
        return f"ssh -i {identity} -o IdentitiesOnly=yes"
    return "ssh"


def _rsync_args(manifest: SiteManifest, dry_run: bool) -> list[str]:
    local = manifest.local_static_path
    if not local.is_dir():
        raise FileNotFoundError(f"Local static path not found: {local}")

    remote = manifest.static.remote.rstrip("/") + "/"
    target = f"{_ssh_target(manifest)}:{remote}"

    args = [
        "rsync",
        "-az",
        "--delete",
        "-e",
        _ssh_command(),
        "--human-readable",
        "--progress" if os.isatty(1) else "--info=stats2",
    ]
    if dry_run:
        args.append("--dry-run")
    for pattern in manifest.static.excludes:
        args.extend(["--exclude", pattern])
    args.extend([f"{local}/", target])
    return args


def deploy_rsync(manifest: SiteManifest, dry_run: bool = False) -> subprocess.CompletedProcess:
    cmd = _rsync_args(manifest, dry_run=dry_run)
    result = subprocess.run(cmd, check=False, text=True)
    if result.returncode == 0 and not dry_run:
        write_deploy_state(
            manifest.name,
            last_deploy_ok=True,
            transport="rsync",
            remote=manifest.static.remote,
            local=str(manifest.local_static_path),
        )
    elif result.returncode != 0:
        write_deploy_state(manifest.name, last_deploy_ok=False, transport="rsync")
    return result


def deploy_ftp(manifest: SiteManifest, dry_run: bool = False) -> int:
    """FTP deploy via lftp mirror (fallback for legacy sites)."""
    server = manifest.static.ftp_server
    user = manifest.static.ftp_user or os.environ.get("HOST_FTP_USER")
    password = os.environ.get("HOST_FTP_PASSWORD") or os.environ.get("FTP_PASSWORD")
    remote_dir = manifest.static.ftp_remote_dir or manifest.static.remote

    if not all([server, user, password, remote_dir]):
        raise ValueError(
            "FTP deploy requires static.ftp_server, ftp_user, ftp_remote_dir "
            "and HOST_FTP_PASSWORD (or FTP_PASSWORD) in env."
        )

    local = manifest.local_static_path
    if dry_run:
        print(f"FTP dry-run: would mirror {local} -> {server}:{remote_dir}")
        return 0

    script = f"""
set ftp:ssl-allow no
open -u {user},{password} {server}
lcd {local}
cd {remote_dir}
mirror --reverse --delete --verbose
bye
"""
    result = subprocess.run(
        ["lftp", "-c", script.strip()],
        check=False,
        text=True,
    )
    if result.returncode == 0:
        write_deploy_state(
            manifest.name,
            last_deploy_ok=True,
            transport="ftp",
            remote=remote_dir,
            local=str(local),
        )
    return result.returncode


def deploy_site(manifest: SiteManifest, dry_run: bool = False) -> int:
    transport = manifest.static.transport.lower()
    if transport == "rsync":
        result = deploy_rsync(manifest, dry_run=dry_run)
        return result.returncode
    if transport == "ftp":
        return deploy_ftp(manifest, dry_run=dry_run)
    raise ValueError(f"Unknown transport: {transport}")


def _ssh_argv(remote_command: str, manifest: SiteManifest) -> list[str]:
    target = _ssh_target(manifest)
    identity = os.environ.get("HOST_SSH_IDENTITY_FILE", "").strip()
    argv = ["ssh", "-o", "BatchMode=yes"]
    if identity:
        argv.extend(["-i", identity, "-o", "IdentitiesOnly=yes"])
    argv.extend([target, remote_command])
    return argv


def remote_prepare_wordpress(manifest: SiteManifest, *, backup: bool = True) -> int:
    """Backup public_html and remove WordPress index.php / wp-* before static deploy."""
    remote = manifest.static.remote.rstrip("/")
    parts: list[str] = []
    if backup:
        parts.append(
            f"tar czf ~/wp-backup-$(date +%Y%m%d%H%M).tar.gz -C {remote} . "
            "2>/dev/null || true"
        )
    parts.extend(
        [
            f"rm -f {remote}/index.php",
            f"rm -rf {remote}/wp-admin {remote}/wp-content {remote}/wp-includes",
            f"rm -f {remote}/wp-*.php {remote}/xmlrpc.php",
            f"ls -la {remote}/index.* 2>/dev/null || true",
        ]
    )
    script = " && ".join(parts)
    result = subprocess.run(_ssh_argv(script, manifest), check=False, text=True)
    return result.returncode


def validate_manifest(manifest: SiteManifest) -> list[str]:
    issues: list[str] = []
    local = manifest.local_static_path
    if not local.is_dir():
        issues.append(f"Local static path missing: {local}")
    if manifest.static.transport == "rsync":
        if not (manifest.static.ssh_user or default_ssh_user()):
            issues.append("SSH user not set for rsync deploy")
    return issues
