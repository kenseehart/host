# Agent onboarding — Host platform

Cross-project static hosting, rsync deploy, and Claude.ai MCP for site management.

## Shared resources

Workspace index: **`/home/ken/AGENTS.md`**. OAuth helper: **`/home/ken/shared/mcp`** (`ken-mcp` package).

## What this project is

**Host** — scaffold static sites, deploy to [my.hosting.com](https://my.hosting.com/) via rsync, and manage sites from Claude mobile through Host MCP on seehart.com.

## Repo

- Path: **`/home/ken/host`**
- GitHub: kenseehart/host (create on first push)

## Quick start

```bash
cd ~/host
source .venv/bin/activate   # puts sitehost on PATH
sitehost -h
sitehost sites
```

Without activating the venv:

```bash
cd ~/host
uv run sitehost -h          # recommended
# or
.venv/bin/sitehost sites
```

Locate the module: `whip host.sitehost` (not `whip host` — that hits `/usr/bin/host`).

## MCP

```bash
uv run python -m host.sitehost serve
```

Deploy on seehart.com at `/host/mcp`. See **`docs/hosting.md`**.

Tools: `host_list_sites`, `host_status`, `host_deploy`, `host_scaffold`.

## Consumers

| Site | Repo | Manifest |
|------|------|----------|
| gameofy | `/home/ken/y` | `host.yaml` |
| seehart | `/home/ken/seehart` | `host.yaml` |

Registry: `~/.config/ken/host/sites.yaml`

## Conventions

- Static HTML only — no mandatory npm build
- `host.yaml` per consumer project
- rsync primary; FTP fallback for legacy
- Personal OAuth via `ken_mcp.PersonalAuthProvider`
