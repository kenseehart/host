"""Domain inventory config — ownership, hosting, and docroot metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_DOMAINS = Path.home() / ".config" / "ken" / "host" / "domains.yaml"


@dataclass
class DomainEntry:
    domain: str
    owner: str = "ken"
    hosting: str = "a2"
    docroot: str | None = None
    registrar: str | None = None
    dns_host: str | None = None
    notes: str | None = None
    site_name: str | None = None


def load_domains(path: Path | str | None = None) -> list[DomainEntry]:
    config_path = Path(path or DEFAULT_DOMAINS)
    if not config_path.is_file():
        return []
    data = yaml.safe_load(config_path.read_text()) or {}
    entries: list[DomainEntry] = []
    for item in data.get("domains", []):
        entries.append(
            DomainEntry(
                domain=item["domain"],
                owner=item.get("owner", "ken"),
                hosting=item.get("hosting", "a2"),
                docroot=item.get("docroot"),
                registrar=item.get("registrar"),
                dns_host=item.get("dns_host"),
                notes=item.get("notes"),
                site_name=item.get("site_name"),
            )
        )
    return entries


def filter_domains(
    entries: list[DomainEntry],
    *,
    owner: str | None = None,
    hosting: str | None = None,
) -> list[DomainEntry]:
    rows = entries
    if owner:
        rows = [e for e in rows if e.owner == owner]
    if hosting:
        rows = [e for e in rows if e.hosting == hosting]
    return rows


def domain_rows(entries: list[DomainEntry]) -> list[dict[str, Any]]:
    return [
        {
            "domain": e.domain,
            "owner": e.owner,
            "hosting": e.hosting,
            "docroot": e.docroot or "",
            "registrar": e.registrar or "",
            "dns_host": e.dns_host or "",
            "site_name": e.site_name or "",
            "notes": e.notes or "",
        }
        for e in entries
    ]
