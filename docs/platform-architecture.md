# Platform architecture — hosting + compute

Decisions from the seehart.com hosting rollout (2026-06). This is the canonical summary; detail lives in linked docs.

## Two platforms, no third tier

| Platform | Repo | Runs |
|----------|------|------|
| **host** (hosting.com) | [`host/`](../) | Static sites (rsync CI); **thin Python** MCP/orchestration |
| **compute** (GCP / RunPod) | [`compute`](../../compute/AGENTS.md) | GPU, batch, PRISM training, Jupyter |

**No separate VPS or “powerful hosting” product** unless hosting.com Python fails the Phase 2 experiment — then optional `mcp-services` on GCP ([`services-mcp.md`](services-mcp.md)).

Home physical server GPUs are **out of production scope**; use `daime-gpu` (GCP) or `daime-prism` (RunPod).

## Thin orchestrator (hosting.com)

Shared hosting can run Python at **ordinary website compute** — MCP protocol, OAuth, deploy triggers, light I/O. Anything heavier **delegates to `compute`**:

```bash
compute up daime-gpu
compute run daime-gpu 'cd ~/daime && uv run python -m hinario ...'
```

Never run Whisper, PRISM training, or large embeddings on the hosting.com Python process.

## MCP: Cursor vs Claude.ai

| Client | Transport | Where |
|--------|-----------|-------|
| **Cursor** | stdio (local) | `.cursor/mcp.json` |
| **Claude.ai / mobile** | HTTPS + OAuth | hosting.com Python app (target: `https://seehart.com/host/mcp`) |

Do **not** point Claude.ai at Cursor’s local MCP processes.

## Rollout phases

| Phase | Goal | Doc |
|-------|------|-----|
| **1** | Static site on seehart.com (replace WP), CI rsync | [`hosting.md`](hosting.md), [`seehart/docs/SETUP.md`](../../seehart/docs/SETUP.md) |
| **2** | hosting.com Python MCP experiment | [`hosting-python.md`](hosting-python.md) |
| **3** | Claude.ai connectors | **Deferred** until Phase 2 confirms URL + OAuth |
| **4** | Other static sites (y, nfnc, …) | [`phase4-static-sites.md`](phase4-static-sites.md) |

Phase 1 bootstrap: `sitehost setup-deploy --ssh-user CPANEL_USER` → deploy key + `host.env` + GitHub secrets.

## Domain registration

**Standard registrar:** [Cloudflare](domains-and-dns.md) — new Ken domains register there; existing domains transfer at renewal (~$10.44/yr .com at-cost). DNS on Cloudflare NS; A record → A2 hosting.

## RunPod: `daime-prism`

Live pod for daime + fish PRISM work:

| Spec | Value |
|------|-------|
| Template | `runpod-torch-v280` — **JupyterLab + PyTorch pre-installed** (port 8888) |
| GPU | NVIDIA L4 |
| RAM | 86 GB |
| Volume | `daime_prism_volume` (50 GB) → `/workspace` |
| Cost | ~$0.39/hr |

Bind an **existing** pod (IP/port change on restart):

```bash
compute bind daime-prism --ssh root@HOST:PORT \
  --proxy-user PODUSER --identity ~/.ssh/id_ed25519_personal
compute ssh daime-prism
compute tunnel daime-prism --port 8888   # Jupyter → http://127.0.0.1:8888
```

Prefer **SSH over exposed TCP** for rsync/SCP; proxy SSH (`user@ssh.runpod.io`) is stored as fallback.

## Workload routing (quick reference)

| Workload | Where |
|----------|-------|
| Consumer static HTML | hosting.com rsync |
| MCP HTTP + OAuth | hosting.com Python (Phase 2) |
| GPU ASR, training | `compute` (`daime-gpu`, `daime-prism`) |
| Fish PRISM | `fish/compute.yaml` → `daime-prism` |
| MCP fallback | GCP `mcp-services` — only if Phase 2 fails |

## Open items (manual)

- [x] Phase 1 seehart.com static deploy (`~/seehart.com`, CI secrets)
- [ ] Phase 2: cPanel Python app at `/host`; fill checklist in `hosting-python.md`
- [ ] Cloudflare account + API token for registrar (see `domains-and-dns.md`)
- [ ] Migrate Ken domains to Cloudflare at renewal (see `sitehost inventory --columns domain,renewal`)
- [ ] `MONGODB_URI` in `~/.config/compute/secrets.yaml` for `compute run` job tracking

Next session: [`NEXT-STEPS.md`](NEXT-STEPS.md)
