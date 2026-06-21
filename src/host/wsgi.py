"""ASGI/WSGI entry for hosting.com Python apps (Passenger / LiteSpeed)."""

from __future__ import annotations

from a2wsgi import ASGIMiddleware

from host.mcp_server import build_mcp

_mcp = build_mcp()
_asgi = _mcp.http_app(transport="streamable-http")
application = ASGIMiddleware(_asgi)
