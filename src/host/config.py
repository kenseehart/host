from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

CONFIG_ENV = Path.home() / ".config" / "ken" / "host" / "host.env"


def load_env() -> None:
    if CONFIG_ENV.is_file():
        load_dotenv(CONFIG_ENV)
    load_dotenv()


def mcp_base_url() -> str:
    return os.getenv("HOST_MCP_BASE_URL", "https://seehart.com/host")


def mcp_client_id() -> str:
    return os.getenv("HOST_MCP_CLIENT_ID", "host-mcp")


def mcp_client_secret() -> str:
    return os.getenv("HOST_MCP_CLIENT_SECRET", "")


def mcp_host() -> str:
    return os.getenv("HOST_MCP_HOST", "0.0.0.0")


def mcp_port() -> int:
    return int(os.getenv("HOST_MCP_PORT", "8754"))


def oauth_state_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("HOST_OAUTH_STATE_DIR", "~/.config/ken/host/oauth-state")))


def git_status(repo: Path) -> dict:
    if not (repo / ".git").exists():
        return {"is_git": False}
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "is_git": True,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "changed_files": len(status.stdout.strip().splitlines()) if status.stdout.strip() else 0,
    }
