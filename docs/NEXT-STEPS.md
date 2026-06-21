# NEXT-STEPS — workspace operational queue

Say **`next step`** in any Cursor chat (new or ongoing). The agent reads this file and executes it.

## Instructions for agents

1. Read this file first — do not ask Ken to paste a prompt.
2. Work **only the first item** in **Do next** below.
3. Use **Decisions**, **Completed**, and **Key paths** for context; do not redo finished work.
4. Verify each item's **Done when** with commands or evidence.
5. On success: move the item to **Completed** (one line) and remove it from **Do next**; save this file.
6. If blocked: add **`Blocked:`** under the item with reason and what Ken must do; stop — do not skip ahead.
7. Never put secrets in this file — reference paths only (`~/.config/...`).
8. Mark `[user]` when Ken must act manually (DNS UI, Claude settings); otherwise agent executes.

---

## Decisions (locked in)

- **MCP gateway:** GCP `mcp-services` VM at `https://mcp.seehart.com` (Phase 2 hosting.com Passenger blocked)
- **Two platforms:** `host` (A2 static) + `compute` (GCP/RunPod). MCP HTTP on GCP e2-small always-on.
- **Claude.ai:** five HTTPS OAuth connectors (host, tesla, fish, nfnc, bridge)
- **Cursor tunnel:** `bridge` MCP → Cursor cloud agents via `cursor-sdk`
- **GCP project:** `agi-green`
- **Standard registrar:** Cloudflare — see [`domains-and-dns.md`](domains-and-dns.md)

## Completed

| Item | Status |
|------|--------|
| Phase 1 seehart.com static | ✅ https://seehart.com |
| Docroot guard (`~/public_html`) | ✅ |
| `cmdline.progress` pushed | ✅ shared repo |
| MCP gateway code + deploy CLI | ✅ `sitehost deploy-mcp-gateway` |
| Security hardening (fail-closed, no /register) | ✅ ken_mcp |
| `bridge/` Cursor tunnel MCP | ✅ |
| nfnc HTTP MCP | ✅ |
| gcloud installed; `GCP_PROJECT=agi-green` | ✅ |
| Bootstrap `mcp-services` GCP VM | ✅ static IP `34.60.252.117`, nginx + certbot + python3-venv |
| DNS + TLS for `mcp.seehart.com` | ✅ Let's Encrypt; HTTP→HTTPS redirect |
| Configure gateway secrets | ✅ dry-run passes; synced to VM |
| Deploy MCP gateway | ✅ 5 systemd units active; `/host/mcp` → 401 |

## Do next

### [user] Register Claude.ai connectors

**Do:** Manual — [`claude-connectors.md`](claude-connectors.md). Phone E2E: host inventory + bridge `agent_run`.

**Done when:** All five connectors connected and tools work from phone.

---

### [agent] Decommission seehart.com `/host` Passenger app

**Do:** Remove non-functional cloudlinux app on seehart.com; confirm static site still OK.

**Done when:** MCP only via `mcp.seehart.com`.

---

### Phase 4 static sites + Cloudflare registrar

See [`phase4-static-sites.md`](phase4-static-sites.md), [`domains-and-dns.md`](domains-and-dns.md).

## Key paths

| Path | Purpose |
|------|---------|
| [`services-mcp.md`](services-mcp.md) | Gateway runbook |
| [`claude-connectors.md`](claude-connectors.md) | Claude.ai registration |
| [`../../bridge/AGENTS.md`](../../bridge/AGENTS.md) | Cursor tunnel MCP |
| [`../../compute/resources.yaml`](../../compute/resources.yaml) | `mcp-services` resource |
| `~/.config/ken/host/host.env` | Deploy + MCP secrets |
| `~/.config/compute/secrets.yaml` | `GCP_PROJECT`, RunPod |
