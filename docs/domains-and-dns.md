# Domains, DNS, and automated site spin-up

## Recommended pattern for full automation

**Best single-vendor path:** [Cloudflare Registrar](https://developers.cloudflare.com/registrar/) + Cloudflare DNS API.

| Step | Tool | Why |
|------|------|-----|
| Register domain | Cloudflare Registrar API | One API for buy + renew |
| DNS records | Cloudflare DNS API | A/CNAME to A2 IP, TXT for ACME |
| Addon domain + docroot | A2 cPanel UAPI (SSH) | Mount site on shared hosting |
| Scaffold + deploy | `sitehost mkweb` + GitHub CI | Static vibe-coded site |

**Alternative registrar API:** [Porkbun API](https://porkbun.com/api/json/v3/documentation) — cheap, good for `.com`, register + DNS in one place.

**What A2 alone cannot do:** domain registration. A2/cPanel only manages DNS **after** nameservers point to `ns1–4.a2hosting.com`.

## Current DNS hosting (2026-06)

| DNS host | Domains (examples) | Edit in |
|----------|-------------------|---------|
| **A2** (`ns*.a2hosting.com`) | seehart, yknotlabs, agi.green, zillionsofgames, geometrian, wondercamp | cPanel → Zone Editor |
| **GoDaddy** | gameofy.com | GoDaddy DNS |
| **Azure DNS** | evolver.ai | Azure portal |
| **Other** | nfnc.com, busybear, manymind | Respective panels |

Ken-owned sites on A2: seehart.com, agi.green, yknotlabs.com, wondercamp.site. nfnc.com DNS is off-A2.

## Ownership config

Edit **`~/.config/ken/host/domains.yaml`** (template: [`templates/domains.yaml.example`](../templates/domains.yaml.example)).

```yaml
domains:
  - domain: seehart.com
    owner: ken
    hosting: a2
    docroot: ~/seehart.com
    site_name: seehart
```

Jeff/shared domains can be listed with `owner: jeff` for visibility — do not deploy without coordination.

## Inventory commands

```bash
sitehost inventory                    # Ken domains, live probes
sitehost inventory --owner jeff       # Jeff/shared visibility
sitehost inventory --json             # JSON output
sitehost inventory --md               # Markdown table
sitehost inventory --columns domain,up,renewal,dns_host
sitehost inventory --no-probe         # Config only, no network
```

MCP: `host_inventory(owner="ken", format="text|md|json", columns="domain,up,renewal")`

## Prompt → new site workflow (target)

1. Agent picks available domain (or calls registrar API to register via Cloudflare/Porkbun).
2. Set A record → A2 server IP; optional `sitehost` validates DNS.
3. cPanel addon domain → docroot path recorded in `domains.yaml`.
4. `sitehost mkweb "My Site" --domain example.com --remote ~/example.com`.
5. Vibe-code in `site/`; push to `main` → CI rsync deploy.
6. `host_inventory` confirms `up=true`.

Registrar API keys belong in `~/.config/ken/host/secrets.yaml` (future) — not in repo.

## Phase 2 MCP

`host_inventory` is available on Host MCP once Phase 2 deploys to `seehart.com/host/mcp`.
