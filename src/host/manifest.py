from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REQUIRED_MANIFEST_KEYS = ("name", "domain", "static")


@dataclass
class StaticTarget:
    local: str
    remote: str
    transport: str = "rsync"
    ssh_host: str | None = None
    ssh_user: str | None = None
    excludes: list[str] = field(default_factory=list)
    ftp_server: str | None = None
    ftp_user: str | None = None
    ftp_remote_dir: str | None = None


@dataclass
class ServiceTarget:
    name: str
    module: str
    port: int
    path: str
    domain: str


@dataclass
class SiteManifest:
    name: str
    domain: str
    static: StaticTarget
    services: list[ServiceTarget] = field(default_factory=list)
    repo_root: Path | None = None

    @property
    def local_static_path(self) -> Path:
        if self.repo_root is None:
            raise ValueError("repo_root not set on manifest")
        return (self.repo_root / self.static.local).resolve()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "domain": self.domain,
            "static": {
                "local": self.static.local,
                "remote": self.static.remote,
                "transport": self.static.transport,
            },
        }
        if self.static.ssh_host:
            data["static"]["ssh_host"] = self.static.ssh_host
        if self.static.ssh_user:
            data["static"]["ssh_user"] = self.static.ssh_user
        if self.static.excludes:
            data["static"]["excludes"] = self.static.excludes
        if self.services:
            data["services"] = [
                {
                    "name": s.name,
                    "module": s.module,
                    "port": s.port,
                    "path": s.path,
                    "domain": s.domain,
                }
                for s in self.services
            ]
        return data


def _parse_static(data: dict[str, Any]) -> StaticTarget:
    return StaticTarget(
        local=data["local"],
        remote=data["remote"],
        transport=data.get("transport", "rsync"),
        ssh_host=data.get("ssh_host"),
        ssh_user=data.get("ssh_user"),
        excludes=list(data.get("excludes", [])),
        ftp_server=data.get("ftp_server"),
        ftp_user=data.get("ftp_user"),
        ftp_remote_dir=data.get("ftp_remote_dir"),
    )


def _parse_services(data: list[dict[str, Any]] | None) -> list[ServiceTarget]:
    if not data:
        return []
    return [
        ServiceTarget(
            name=item["name"],
            module=item["module"],
            port=int(item["port"]),
            path=item["path"],
            domain=item["domain"],
        )
        for item in data
    ]


def load_manifest(path: Path | str, repo_root: Path | str | None = None) -> SiteManifest:
    path = Path(path)
    raw = yaml.safe_load(path.read_text()) or {}
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in raw:
            raise ValueError(f"host.yaml missing required key: {key}")
    root = Path(repo_root) if repo_root else path.parent
    return SiteManifest(
        name=raw["name"],
        domain=raw["domain"],
        static=_parse_static(raw["static"]),
        services=_parse_services(raw.get("services")),
        repo_root=root.resolve(),
    )


def find_manifest(start: Path | str | None = None) -> Path | None:
    cwd = Path(start or Path.cwd()).resolve()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / "host.yaml"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def default_ssh_user() -> str:
    return os.environ.get("HOST_SSH_USER", os.environ.get("USER", ""))


def default_ssh_host(domain: str) -> str:
    return os.environ.get("HOST_SSH_HOST", domain)
