# Host platform deploy — seehart.com MCP + rsync static sites

Pattern matches [tesla/README.md](../tesla/README.md) and [fish/docs/deploy.md](../fish/docs/deploy.md).

## Prerequisites

- SSH access to my.hosting.com (rsync to docroot)
- `uv` on dev machine and hosting server (for MCP)
- GitHub repo secrets for CI deploy

## Site manifest (`host.yaml`)

Each consumer project has a `host.yaml`:

```yaml
name: mysite
domain: example.com
static:
  local: site          # path inside repo
  remote: ~/public_html
  transport: rsync     # or ftp for legacy
  ssh_host: example.com
  ssh_user: cpanel-user
  excludes:
    - ".git"
```

## CLI

```bash
cd /home/ken/host
uv sync
uv run python -m util.mkdo_setup
mkdo host.sitehost -d .venv/bin

sitehost mkweb "My Site" --domain example.com
sitehost validate
sitehost deploy --dry-run
sitehost sites
host register mysite --repo /home/ken/example
```

## Registry

`~/.config/ken/host/sites.yaml` maps logical names to repo paths for Host MCP:

```yaml
sites:
  - name: gameofy
    repo: /home/ken/y
    manifest: host.yaml
  - name: seehart
    repo: /home/ken/seehart
    manifest: host.yaml
```

## Host MCP (Claude.ai / mobile)

### Env

Copy [host.env.example](host.env.example) to `~/.config/ken/host/host.env`.

### Run locally

```bash
cd /home/ken/host
sitehost serve
```

### systemd (on hosting)

```ini
[Unit]
Description=Host MCP HTTP
After=network.target

[Service]
WorkingDirectory=/home/ken/host
EnvironmentFile=/home/ken/.config/ken/host/host.env
ExecStart=/home/ken/host/.venv/bin/sitesitehost serve
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### nginx

```nginx
location /host/ {
    proxy_pass http://127.0.0.1:8754/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

OAuth endpoints (`/authorize`, `/token`, etc.) proxy the same way as [tesla/README.md](../tesla/README.md).

### Claude.ai connector

1. Settings → Connectors → Add custom connector
2. URL: `https://seehart.com/host/mcp`
3. Advanced Settings: `HOST_MCP_CLIENT_ID` + `HOST_MCP_CLIENT_SECRET`

## GitHub Actions CI

`host mkweb` copies `.github/workflows/deploy-<slug>.yml`. Required secrets:

| Secret | Purpose |
|--------|---------|
| `SSH_PRIVATE_KEY` | Deploy key for rsync |
| `HOST_SSH_USER` | cPanel / SSH username |
| `HOST_SSH_HOST` | SSH hostname (often same as domain) |

For legacy FTP sites, set `transport: ftp` in host.yaml and use `FTP_PASSWORD` / `HOST_FTP_PASSWORD`.

## Verify SSH docroot

Before first deploy, confirm remote path:

```bash
ssh user@seehart.com 'ls -la ~/public_html'
```

Adjust `static.remote` in host.yaml to match your hosting panel layout.
