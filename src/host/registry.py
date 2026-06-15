from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from host.manifest import SiteManifest, find_manifest, load_manifest

DEFAULT_REGISTRY = Path.home() / ".config" / "ken" / "host" / "sites.yaml"


@dataclass
class SiteEntry:
    name: str
    repo: str
    manifest: str = "host.yaml"


def load_registry(path: Path | str | None = None) -> list[SiteEntry]:
    registry_path = Path(path or DEFAULT_REGISTRY)
    if not registry_path.is_file():
        return []
    data = yaml.safe_load(registry_path.read_text()) or {}
    sites = data.get("sites", [])
    return [
        SiteEntry(
            name=item["name"],
            repo=item["repo"],
            manifest=item.get("manifest", "host.yaml"),
        )
        for item in sites
    ]


def save_registry(entries: list[SiteEntry], path: Path | str | None = None) -> None:
    registry_path = Path(path or DEFAULT_REGISTRY)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sites": [
            {"name": e.name, "repo": e.repo, "manifest": e.manifest}
            for e in entries
        ]
    }
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False))


def register_site(name: str, repo: str, manifest: str = "host.yaml") -> None:
    entries = load_registry()
    entries = [e for e in entries if e.name != name]
    entries.append(SiteEntry(name=name, repo=repo, manifest=manifest))
    save_registry(entries)


def resolve_manifest(site_name: str | None = None, cwd: Path | None = None) -> SiteManifest:
    if site_name:
        for entry in load_registry():
            if entry.name == site_name:
                repo = Path(entry.repo).expanduser().resolve()
                return load_manifest(repo / entry.manifest, repo_root=repo)
        raise KeyError(f"Site not in registry: {site_name}")

    manifest_path = find_manifest(cwd)
    if manifest_path is None:
        raise FileNotFoundError("No host.yaml found in current directory or parents")
    return load_manifest(manifest_path)


def registry_status() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in load_registry():
        repo = Path(entry.repo).expanduser()
        manifest_path = repo / entry.manifest
        row: dict[str, Any] = {
            "name": entry.name,
            "repo": str(repo),
            "manifest": str(manifest_path),
            "manifest_exists": manifest_path.is_file(),
            "repo_exists": repo.is_dir(),
        }
        if manifest_path.is_file():
            try:
                m = load_manifest(manifest_path, repo_root=repo)
                row["domain"] = m.domain
                row["local_static"] = str(m.local_static_path)
                row["transport"] = m.static.transport
            except Exception as exc:
                row["error"] = str(exc)
        rows.append(row)
    return rows
