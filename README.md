# Host platform

Static site scaffolding, rsync deploy to my.hosting.com, and Host MCP for Claude.ai site management.

```bash
cd /home/ken/host
uv sync
uv run python -m util.mkdo_setup
mkdo host.sitehost -d .venv/bin

sitehost mkweb "My Site" --domain example.com
sitehost deploy --dry-run
```

See **`docs/hosting.md`** and **`AGENTS.md`**.
