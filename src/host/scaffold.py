from __future__ import annotations

import shutil
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = PACKAGE_ROOT / "templates"


def _replace_placeholders(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def scaffold_static_site(
    name: str,
    domain: str,
    target_dir: Path | None = None,
    remote_path: str | None = None,
) -> Path:
    """Create site/ + host.yaml + GitHub workflow from static-site template."""
    cwd = (target_dir or Path.cwd()).resolve()
    site_name = name.lower().replace(" ", "-")
    mapping = {
        "SITE_NAME": name,
        "SITE_SLUG": site_name,
        "DOMAIN": domain,
        "REMOTE_PATH": remote_path or f"~/public_html/{site_name}",
    }

    site_dir = cwd / "site"
    template_site = TEMPLATES_DIR / "static-site" / "site"
    if site_dir.exists():
        raise FileExistsError(f"Site directory already exists: {site_dir}")
    shutil.copytree(template_site, site_dir)

    for path in site_dir.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".css", ".js", ".md"}:
            path.write_text(_replace_placeholders(path.read_text(), mapping))

    host_yaml = TEMPLATES_DIR / "static-site" / "host.yaml"
    manifest_text = _replace_placeholders(host_yaml.read_text(), mapping)
    (cwd / "host.yaml").write_text(manifest_text)

    workflow_src = TEMPLATES_DIR / "github-workflow" / "deploy.yml"
    workflow_dir = cwd / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_text = _replace_placeholders(workflow_src.read_text(), mapping)
    (workflow_dir / f"deploy-{site_name}.yml").write_text(workflow_text)

    return cwd


def scaffold_template_tree(template: str = "static-site") -> dict[str, str]:
    """Return template file paths and contents for MCP/agents."""
    root = TEMPLATES_DIR / template
    if not root.is_dir():
        raise FileNotFoundError(f"Unknown template: {template}")
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(TEMPLATES_DIR))
            files[rel] = path.read_text()
    workflow = TEMPLATES_DIR / "github-workflow" / "deploy.yml"
    if workflow.is_file():
        files["github-workflow/deploy.yml"] = workflow.read_text()
    return files
