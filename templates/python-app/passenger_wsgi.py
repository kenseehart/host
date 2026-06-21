"""cPanel / Passenger entry — copy to Python app root on hosting.com.

Ensures the CloudLinux app virtualenv site-packages are on sys.path before import.
Set HOST_MCP_* via ~/.config/ken/host/host.env (synced by sitehost deploy-mcp).
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
APP_NAME = APP_ROOT.name  # e.g. host-mcp
PY_TAG = f"{sys.version_info.major}.{sys.version_info.minor}"

VENV_SITE = (
    Path.home()
    / "virtualenv"
    / APP_NAME
    / PY_TAG
    / "lib"
    / f"python{PY_TAG}"
    / "site-packages"
)
for entry in (VENV_SITE, APP_ROOT):
    path = str(entry)
    if path not in sys.path:
        sys.path.insert(0, path)

from host.wsgi import application  # noqa: E402
