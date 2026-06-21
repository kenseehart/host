"""Provision Fish cloud corpus on GCP mcp-services (PD + migrate + sync timer)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

RESOURCE = "mcp-services"
DISK_NAME = "fish-data"
DISK_SIZE_GB = 100
MOUNT_POINT = "/data/fish"
REMOTE_APP = "/home/mcp/mcp-gateway"
LOCAL_FISH_CONFIG = Path.home() / ".config" / "fish"
REMOTE_FISH_CONFIG = "/home/mcp/.config/fish"
FISH_ENV_KEYS = (
    "FISH_DATA_DIR",
    "FISH_DB_PATH",
    "OPENAI_API_KEY",
    "FISH_EMBEDDING_MODEL",
    "FISH_PRISM_MODEL",
    "FISH_MCP_BASE_URL",
    "FISH_MCP_CLIENT_ID",
    "FISH_MCP_CLIENT_SECRET",
)


def _resolve_gcp() -> tuple[str, str, str]:
    from compute.providers.gcp import GcpProvider
    from compute.registry import resolve

    resource, provider = resolve(RESOURCE)
    if not isinstance(provider, GcpProvider):
        raise RuntimeError(f"{RESOURCE} is not a GCP resource")
    project, zone, vm = provider._ssh_base(resource)
    return project, zone, vm


def _run_gcloud(args: list[str]) -> int:
    cmd = ["gcloud", *args]
    print(f"+ {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


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


def _ensure_disk(project: str, zone: str, *, dry_run: bool) -> int:
    result = subprocess.run(
        [
            "gcloud",
            "compute",
            "disks",
            "describe",
            DISK_NAME,
            f"--project={project}",
            f"--zone={zone}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"Disk {DISK_NAME} already exists")
        return 0
    if dry_run:
        print(f"Dry-run: would create disk {DISK_NAME} ({DISK_SIZE_GB}GB pd-standard)")
        return 0
    return _run_gcloud(
        [
            "compute",
            "disks",
            "create",
            DISK_NAME,
            f"--project={project}",
            f"--zone={zone}",
            f"--size={DISK_SIZE_GB}GB",
            "--type=pd-standard",
        ]
    )


def _attach_disk(project: str, zone: str, vm: str, *, dry_run: bool) -> int:
    if dry_run:
        print(f"Dry-run: would attach {DISK_NAME} to {vm}")
        return 0
    return _run_gcloud(
        [
            "compute",
            "instances",
            "attach-disk",
            vm,
            f"--project={project}",
            f"--zone={zone}",
            f"--disk={DISK_NAME}",
            "--device-name=fish-data",
        ]
    )


def _mount_script() -> str:
    return f"""set -e
DISK_ID=/dev/disk/by-id/google-fish-data
sudo mkdir -p {MOUNT_POINT}
if mountpoint -q {MOUNT_POINT}; then
  echo "Already mounted {MOUNT_POINT}"
else
  if ! sudo blkid "$DISK_ID" >/dev/null 2>&1; then
    echo "Formatting new fish-data disk..."
    sudo mkfs.ext4 -F "$DISK_ID"
  fi
  if ! grep -q 'google-fish-data' /etc/fstab; then
    echo "$DISK_ID {MOUNT_POINT} ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
  fi
  sudo mount -a
fi
sudo chown -R mcp:mcp {MOUNT_POINT}
sudo mkdir -p {MOUNT_POINT}/models {MOUNT_POINT}/imports
sudo chown -R mcp:mcp {MOUNT_POINT}
echo "OK — mounted {MOUNT_POINT}"
"""


def _upsert_remote_env(*, dry_run: bool) -> int:
    lines: list[str] = []
    local_env = LOCAL_FISH_CONFIG / "fish.env"
    if local_env.is_file():
        load_dotenv(local_env, override=False)
    values = {
        "FISH_DATA_DIR": MOUNT_POINT,
        "FISH_DB_PATH": f"{MOUNT_POINT}/fish.db",
    }
    for key in FISH_ENV_KEYS:
        val = os.getenv(key, "").strip()
        if val:
            values[key] = val
    for key, val in values.items():
        lines.append(f"{key}={val}")
    body = "\n".join(lines) + "\n"
    if dry_run:
        print(f"Dry-run: would write {REMOTE_FISH_CONFIG}/fish.env")
        return 0
    remote_cmd = (
        f"sudo mkdir -p {REMOTE_FISH_CONFIG} && "
        f"sudo chown mcp:mcp {REMOTE_FISH_CONFIG} && "
        f"cat > /tmp/fish.env << 'FISHEOF'\n{body}FISHEOF\n"
        f"sudo mv /tmp/fish.env {REMOTE_FISH_CONFIG}/fish.env && "
        f"sudo chown mcp:mcp {REMOTE_FISH_CONFIG}/fish.env && "
        f"sudo chmod 600 {REMOTE_FISH_CONFIG}/fish.env"
    )
    return _remote_run(remote_cmd)


def _sync_accounts(*, dry_run: bool) -> int:
    local = LOCAL_FISH_CONFIG / "accounts.yaml"
    if not local.is_file():
        print(f"Skip accounts.yaml — not found at {local}", file=sys.stderr)
        return 0
    if dry_run:
        print(f"Dry-run: would copy {local} to VM")
        return 0
    project, zone, vm = _resolve_gcp()
    remote = f"{vm}:/tmp/accounts.yaml"
    scp = [
        "gcloud",
        "compute",
        "scp",
        str(local),
        remote,
        f"--project={project}",
        f"--zone={zone}",
        "--tunnel-through-iap",
    ]
    print(f"+ {' '.join(scp)}")
    if subprocess.run(scp).returncode != 0:
        return 1
    return _remote_run(
        f"sudo mkdir -p {REMOTE_FISH_CONFIG} && "
        f"sudo mv /tmp/accounts.yaml {REMOTE_FISH_CONFIG}/accounts.yaml && "
        f"sudo chown mcp:mcp {REMOTE_FISH_CONFIG}/accounts.yaml && "
        f"sudo chmod 600 {REMOTE_FISH_CONFIG}/accounts.yaml"
    )


def _migrate_db(*, dry_run: bool, force: bool) -> int:
    local_db = LOCAL_FISH_CONFIG / "fish.db"
    if not local_db.is_file():
        print(f"No local fish.db at {local_db} — skip migration", file=sys.stderr)
        return 0
    if dry_run:
        size_gb = local_db.stat().st_size / (1024**3)
        print(f"Dry-run: would upload fish.db ({size_gb:.1f} GB) to {MOUNT_POINT}/")
        return 0

    project, zone, vm = _resolve_gcp()
    check = _remote_run(f"test -f {MOUNT_POINT}/fish.db")
    if check == 0 and not force:
        print(f"Remote fish.db already exists — skip (use --force-migrate to overwrite)")
        return 0

    print(f"Uploading {local_db} (~{local_db.stat().st_size / (1024**3):.1f} GB) — this may take a while...")
    remote_tmp = f"{vm}:/tmp/fish.db"
    scp = [
        "gcloud",
        "compute",
        "scp",
        str(local_db),
        remote_tmp,
        f"--project={project}",
        f"--zone={zone}",
        "--tunnel-through-iap",
    ]
    print(f"+ {' '.join(scp)}")
    if subprocess.run(scp).returncode != 0:
        return 1
    return _remote_run(
        f"sudo mv /tmp/fish.db {MOUNT_POINT}/fish.db && "
        f"sudo chown mcp:mcp {MOUNT_POINT}/fish.db && "
        f"sudo chmod 600 {MOUNT_POINT}/fish.db"
    )


def _install_sync_timer(template_dir: Path, *, dry_run: bool) -> int:
    service = (template_dir / "fish-sync.service").read_text()
    timer = (template_dir / "fish-sync.timer").read_text()
    if dry_run:
        print("Dry-run: would install fish-sync.service + fish-sync.timer")
        return 0
    script = (
        f"cat > /tmp/fish-sync.service << 'EOF'\n{service}EOF\n"
        f"cat > /tmp/fish-sync.timer << 'EOF'\n{timer}EOF\n"
        "sudo mv /tmp/fish-sync.service /etc/systemd/system/fish-sync.service\n"
        "sudo mv /tmp/fish-sync.timer /etc/systemd/system/fish-sync.timer\n"
        "sudo systemctl daemon-reload\n"
        "sudo systemctl enable fish-sync.timer\n"
        "sudo systemctl start fish-sync.timer\n"
        "echo 'OK — fish-sync.timer enabled'"
    )
    return _remote_run(script)


def setup_fish_cloud(
    *,
    dry_run: bool = False,
    migrate: bool = True,
    force_migrate: bool = False,
    skip_disk: bool = False,
) -> int:
    """Create fish-data PD, mount on mcp-services, migrate corpus, enable sync timer."""
    template_dir = Path(__file__).resolve().parents[2] / "templates" / "mcp-services"
    if not template_dir.is_dir():
        print(f"Missing templates: {template_dir}", file=sys.stderr)
        return 1

    try:
        from compute.providers.base import ResourceState
        from compute.registry import resolve

        resource, provider = resolve(RESOURCE)
        st = provider.status(resource)
        if st.state != ResourceState.RUNNING:
            if dry_run:
                print(f"VM {RESOURCE} not running — would start it")
            else:
                print(f"Starting {RESOURCE}...")
                provider.start(resource)
        project, zone, vm = _resolve_gcp()
    except Exception as exc:
        print(f"Cannot reach {RESOURCE}: {exc}", file=sys.stderr)
        return 1

    print(f"Fish cloud setup on {vm} ({zone})")

    if not skip_disk:
        if _ensure_disk(project, zone, dry_run=dry_run) != 0:
            return 1
        if _attach_disk(project, zone, vm, dry_run=dry_run) != 0:
            # already attached is ok
            pass
        if not dry_run and _remote_run(_mount_script()) != 0:
            return 1
        elif dry_run:
            print("Dry-run: would mount /data/fish")

    if _upsert_remote_env(dry_run=dry_run) != 0:
        return 1
    if _sync_accounts(dry_run=dry_run) != 0:
        return 1
    if migrate and _migrate_db(dry_run=dry_run, force=force_migrate) != 0:
        return 1
    if _install_sync_timer(template_dir, dry_run=dry_run) != 0:
        return 1

    print("\nNext steps:")
    print("  sitehost deploy-mcp-gateway")
    print("  compute ssh mcp-services -- sudo systemctl status fish-sync.timer")
    print("  compute sync mcp-services pull fish.db   # training snapshot from RunPod/laptop")
    return 0
