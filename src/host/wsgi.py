"""ASGI/WSGI entry for hosting.com Python apps (Passenger / LiteSpeed)."""

from __future__ import annotations

from host.mcp_server import build_mcp

_mcp = build_mcp()
application = _mcp.http_app(transport="streamable-http")
