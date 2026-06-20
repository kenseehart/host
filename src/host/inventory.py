"""Live probes for domain inventory: DNS, HTTP, WHOIS expiry."""

from __future__ import annotations

import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from host.deploy import read_deploy_state
from host.domains import DomainEntry, domain_rows, filter_domains, load_domains
from host.registry import load_registry, resolve_manifest

DEFAULT_COLUMNS = [
    "domain",
    "owner",
    "dns_host",
    "dns_ok",
    "http_status",
    "up",
    "hosting",
    "docroot",
    "renewal",
    "last_deploy",
    "notes",
]


def _dig_short(record_type: str, name: str) -> list[str]:
    try:
        result = subprocess.run(
            ["dig", "+short", record_type, name, "@8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _infer_dns_host(nameservers: list[str]) -> str:
    if not nameservers:
        return ""
    joined = " ".join(nameservers).lower()
    if "a2hosting" in joined:
        return "a2"
    if "cloudflare" in joined:
        return "cloudflare"
    if "domaincontrol" in joined:
        return "godaddy"
    if "azure-dns" in joined:
        return "azure"
    if "dnsnameservice" in joined:
        return "dnsnameservice"
    if "ui-dns" in joined:
        return "ionos"
    if "hostgator" in joined:
        return "hostgator"
    return nameservers[0]


def _probe_dns(domain: str) -> dict[str, Any]:
    ns = _dig_short("NS", domain)
    a = _dig_short("A", domain)
    aaaa = _dig_short("AAAA", domain)
    dns_host = _infer_dns_host(ns)
    dns_ok = bool(ns or a or aaaa)
    return {
        "nameservers": ", ".join(ns[:4]),
        "dns_host": dns_host,
        "dns_ok": dns_ok,
        "a_records": ", ".join(a[:3]),
    }


def _probe_http(domain: str) -> dict[str, Any]:
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=12) as resp:
                status = resp.status
                return {
                    "http_status": status,
                    "up": 200 <= status < 400,
                    "url": url,
                }
        except urllib.error.HTTPError as exc:
            return {
                "http_status": exc.code,
                "up": 200 <= exc.code < 400,
                "url": url,
            }
        except Exception:
            continue
    return {"http_status": "", "up": False, "url": ""}


def _parse_whois_expiry(text: str) -> str:
    patterns = [
        r"Registry Expiry Date:\s*(.+)",
        r"Registrar Registration Expiration Date:\s*(.+)",
        r"Expiration Date:\s*(.+)",
        r"Expiry Date:\s*(.+)",
        r"renewal date:\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().split()[0]
    return ""


def _probe_renewal(domain: str) -> str:
    try:
        result = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    text = result.stdout or result.stderr
    return _parse_whois_expiry(text)


def _registry_site_for_domain(domain: str) -> str | None:
    from pathlib import Path

    from host.manifest import load_manifest

    for entry in load_registry():
        repo = Path(entry.repo).expanduser()
        manifest = repo / entry.manifest
        if not manifest.is_file():
            continue
        try:
            m = load_manifest(manifest, repo_root=repo)
            if m.domain == domain:
                return entry.name
        except Exception:
            continue
    return None


def _last_deploy(site_name: str | None) -> str:
    if not site_name:
        return ""
    state = read_deploy_state(site_name)
    if not state:
        return ""
    ok = state.get("last_deploy_ok")
    updated = state.get("updated_at", "")
    if ok is True:
        return updated
    if ok is False:
        return f"failed {updated}".strip()
    return updated


def build_inventory_row(entry: DomainEntry) -> dict[str, Any]:
    dns = _probe_dns(entry.domain)
    http = _probe_http(entry.domain)
    site_name = entry.site_name or _registry_site_for_domain(entry.domain)
    row = {
        "domain": entry.domain,
        "owner": entry.owner,
        "hosting": entry.hosting,
        "docroot": entry.docroot or "",
        "registrar": entry.registrar or "",
        "dns_host": entry.dns_host or dns["dns_host"],
        "dns_ok": dns["dns_ok"],
        "nameservers": dns["nameservers"],
        "a_records": dns["a_records"],
        "http_status": http["http_status"],
        "up": http["up"],
        "renewal": _probe_renewal(entry.domain),
        "site_name": site_name or "",
        "last_deploy": _last_deploy(site_name),
        "notes": entry.notes or "",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return row


def inventory_rows(
    *,
    owner: str | None = "ken",
    hosting: str | None = None,
    probe: bool = True,
) -> list[dict[str, Any]]:
    entries = filter_domains(load_domains(), owner=owner, hosting=hosting)
    if not entries:
        return []
    if not probe:
        return domain_rows(entries)
    return [build_inventory_row(entry) for entry in entries]


def default_columns() -> list[str]:
    return list(DEFAULT_COLUMNS)
