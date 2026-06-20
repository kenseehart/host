"""cPanel / Passenger entry — copy to Python app root on hosting.com.

Symlink or pip install the host package into the app virtualenv, then set
HOST_MCP_* env vars in the cPanel Python app configuration.
"""

import sys
from pathlib import Path

# App root on hosting (adjust if your layout differs)
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from host.wsgi import application  # noqa: E402
