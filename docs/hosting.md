# Host platform — static sites + thin Python MCP on hosting.com

Two layers:

| Layer | Where | Tooling |
|-------|-------|---------|
| **Static sites** | hosting.com `~/public_html` | `sitehost deploy` (rsync CI) |
| **Thin Python MCP** | hosting.com Python app | `sitehost serve` / [`templates/python-app/`](templates/python-app/) |
| **Heavy compute** | GCP / RunPod | [`compute`](../compute/AGENTS.md) CLI |

See [hosting-python.md](hosting-python.md) for the Phase 2 MCP experiment on seehart.com.

**Architecture summary:** [platform-architecture.md](platform-architecture.md)

## Phase 1 — static deploy bootstrap

### One-time setup (laptop)

```bash
cd /home/ken/ws/host
sitehost setup-deploy --ssh-user YOUR_CPANEL_USER
# Optional: sitehost setup-deploy --ssh-user USER --apply-gh
```

This creates:

- `~/.config/ken/host/deploy_key` (+ `.pub`)
- `~/.config/ken/host/host.env` (`HOST_SSH_*`, `HOST_MCP_*`)

Add the **public key** in hosting.com → SSH Access → Manage SSH Keys.

### GitHub Actions secrets

| Secret | Value |
|--------|-------|
| `SSH_PRIVATE_KEY` | Contents of `deploy_key` |
| `HOST_SSH_USER` | cPanel username |
| `HOST_SSH_HOST` | `seehart.com` (or SSH hostname) |

Org-level secrets recommended so `seehart`, `y`, etc. share the same trio.

### Site manifest (`host.yaml`)

```yaml
name: seehart
domain: seehart.com
static:
  local: site
  remote: ~/public_html
  transport: rsync
  ssh_host: seehart.com
  ssh_user: your-cpanel-user   # or HOST_SSH_USER env
  excludes:
    - ".git"
```

### WordPress cutover

```bash
set -a && source ~/.config/ken/host/host.env && set +a
sitehost remote-prepare --manifest /home/ken/ws/seehart/host.yaml
sitehost deploy --manifest /home/ken/ws/seehart/host.yaml --dry-run
sitehost deploy --manifest /home/ken/ws/seehart/host.yaml
```

Static sites ship `.htaccess` with `DirectoryIndex index.html` so Apache/LiteSpeed prefers HTML over leftover PHP.

### CLI reference

```bash
sitehost mkweb "My Site" --domain example.com
sitehost validate --site seehart
sitehost deploy --site seehart --dry-run
sitehost setup-deploy --ssh-user USER
sitehost remote-prepare --manifest path/to/host.yaml
sitehost sites
sitehost serve          # local MCP dev
```

## Registry

`~/.config/ken/host/sites.yaml` — sites managed by Host MCP tools.

## Host MCP (Phase 2+)

**Target URL:** `https://seehart.com/host/mcp`

**Claude.ai connectors:** deferred until [hosting-python.md](hosting-python.md) experiment confirms OAuth + stable URL.

### Env

Copy [host.env.example](host.env.example) or use `sitehost setup-deploy`.

### Local dev

```bash
sitehost serve
```

### Production (hosting.com Python app)

Deploy [`templates/python-app/`](templates/python-app/) via cPanel **Setup Python App**. Entry: `passenger_wsgi.py` → `host.wsgi:application`.

## Workload routing

| Workload | Platform |
|----------|----------|
| Static HTML/CSS | hosting.com rsync |
| MCP protocol, OAuth, deploy orchestration | hosting.com Python (thin) |
| GPU ASR, PRISM training, batch jobs | `compute` (`daime-gpu`, `prism-train`) |

MCP tools must **not** run GPU work on hosting.com — delegate via `compute run`.

## Fallback: `mcp-services` on GCP

Only if the hosting.com Python experiment fails. Add `mcp-services` to [`compute/resources.yaml`](../compute/resources.yaml) and DNS `mcp.seehart.com`. See plan scope guard — not the default path.

## Verify SSH docroot

```bash
ssh -i ~/.config/ken/host/deploy_key USER@seehart.com 'ls -la ~/public_html'
```
