# Next session prompt — platform hosting rollout

Copy everything below the line into a new Cursor chat to continue.

---

Continue Ken workspace platform hosting rollout.

## Decisions (locked in)

- **Two platforms:** `host` (A2 static + thin Python MCP) + `compute` (RunPod/GCP). No VPS tier unless Phase 2 fails.
- **Standard registrar:** **Cloudflare** for all new Ken domains; migrate existing domains at renewal (~$10.44/yr .com at-cost). See `host/docs/domains-and-dns.md`.
- **A2 account:** cPanel user `zillions`. **Never deploy to `~/public_html` unless domain docroot is confirmed** — seehart uses `~/seehart.com`; Zillions uses `~/public_html`.
- **Deploy pattern:** static sites via GitHub CI rsync on push to `main`; Claude agent via MCP (`host_inventory`, `host_deploy`, …).
- **Workspace config:** `util/top_of_workspace/` + `init_workspace --force`. Secrets stay local (`.cursor/mcp.json`).

## Completed

| Item | Status |
|------|--------|
| Phase 1 seehart.com static site | ✅ Live at https://seehart.com (`~/seehart.com`) |
| SSH deploy key + GitHub secrets | ✅ `zillions`, secrets on kenseehart/seehart |
| `host.yaml` docroot fix | ✅ Pushed (`remote: ~/seehart.com`) |
| Zillions `public_html` restore | ✅ From `~/wp-backup-202606200927.tar.gz` |
| Domain inventory CLI/MCP | ✅ `sitehost inventory`, `host_inventory` |
| `format_grid` / `format_for_agent` | ✅ shared/cmdline + MCP tools |
| `init_workspace` | ✅ util repo, symlinks active |

## Do next (priority order)

### 1. Verify seehart CI green
- Check GitHub Actions on kenseehart/seehart after `host.yaml` push
- Re-run workflow if needed

### 2. Phase 2 — hosting.com Python MCP
Follow `host/docs/hosting-python.md`:
- cPanel → Setup Python App at `/host` on seehart.com
- Deploy `host/templates/python-app/`
- Set `HOST_MCP_*` from `~/.config/ken/host/host.env`
- Verify `curl -I https://seehart.com/host/mcp` + OAuth discovery
- Fill experiment checklist in `hosting-python.md`

### 3. Phase 3 gate (after Phase 2 passes)
- Register Claude.ai connector at `https://seehart.com/host/mcp`
- Do **not** do this until Phase 2 checklist complete

### 4. Cloudflare setup (registrar standard)
- Open Cloudflare account / API token for Registrar + DNS
- Add token to `~/.config/ken/host/secrets.yaml` (create file)
- Future: `host_register_domain` MCP tool
- Run `sitehost inventory --columns domain,registrar,renewal` — plan migrations at renewal

### 5. Phase 4 static sites
- **y / gameofy:** fix or re-register gameofy.com (GoDaddy, likely expired); yknotlabs.com on A2
- **wondercamp.site, agi.green, carolegolden.com:** inventory + migrate to Cloudflare at renewal
- Use `sitehost mkweb` + correct docroot before any CI deploy

### 6. Compute (parallel)
- `MONGODB_URI` in `~/.config/compute/secrets.yaml`
- Re-bind `daime-prism` if pod restarted: `compute bind daime-prism ...`

## Key paths

| Path | Purpose |
|------|---------|
| `host/docs/platform-architecture.md` | Canonical architecture |
| `host/docs/domains-and-dns.md` | Cloudflare registrar policy |
| `host/docs/hosting-python.md` | Phase 2 experiment |
| `~/.config/ken/host/domains.yaml` | Ken domain inventory |
| `~/.config/ken/host/host.env` | Deploy + MCP secrets |
| `util/top_of_workspace.json` | Workspace symlink manifest |

## Ken domains (`owner: ken`)

seehart.com, agi.green, yknotlabs.com, wondercamp.site, nfnc.com, carolegolden.com, gameofy.com (expired?)

## Not Ken's (inventory only)

malletts.org, geometrian.com, zillionsofgames.com, zillions.com, evolver.ai, busybear.com, manymind.com

## Repos

kenseehart/host, seehart, compute, fish, y, util, shared — workspace `/home/ken/ws`

Start with Phase 2 unless I say otherwise.
