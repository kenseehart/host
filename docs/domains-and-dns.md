# Domains, DNS, and automated site spin-up

## Standard registrar: Cloudflare

**Decision (2026-06):** [Cloudflare Registrar](https://developers.cloudflare.com/registrar/) is the **standard registrar** for all **new** Ken-owned domains and for **migrations at renewal**.

| Policy | Detail |
|--------|--------|
| **New domains** | Register at Cloudflare only |
| **Existing domains** | Migrate to Cloudflare when renewal comes up (transfer in) |
| **DNS** | Cloudflare nameservers (required for Registrar); A/CNAME → A2 hosting IP |
| **Pricing** | At-cost, no markup — **~$10.44/yr** for `.com` (registry + ICANN); renewals same price |
| **Jeff/shared A2 account** | Do not transfer Jeff's domains without coordination |

WHOIS privacy and DNSSEC included. API: [Cloudflare Registrar API](https://developers.cloudflare.com/registrar/) + [DNS API](https://developers.cloudflare.com/api/resources/dns/).

**Not used for new registrations:** GoDaddy, A2-as-registrar, Porkbun (legacy/alternative only if Cloudflare unavailable for a TLD).

## Site hosting vs registration

| Layer | Provider | Role |
|-------|----------|------|
| **Registration + DNS** | Cloudflare (standard) | Buy domain, NS, A record to A2 |
| **Static site files** | A2 / hosting.com | rsync via `sitehost deploy` |
| **Heavy compute** | `compute` (RunPod/GCP) | GPU, batch — never on A2 Python |

A2/cPanel **cannot register domains**. Addon domains + docroots still use cPanel on account `zillions`.

## Automated spin-up workflow (target)

| Step | Tool |
|------|------|
| 1. Register domain | Cloudflare Registrar API |
| 2. DNS A record | Cloudflare DNS API → A2 server IP |
| 3. Addon domain + docroot | A2 cPanel UAPI (SSH) — **confirm docroot path** |
| 4. Record in inventory | `~/.config/ken/host/domains.yaml` (`registrar: cloudflare`) |
| 5. Scaffold | `sitehost mkweb "My Site" --domain example.com --remote ~/example.com` |
| 6. Deploy | Push `main` → GitHub CI rsync |
| 7. Verify | `sitehost inventory --columns domain,up,renewal` |

Registrar API token → `~/.config/ken/host/secrets.yaml` (future MCP tool) — not in repo.

## Current DNS hosting (legacy — migrate on renewal)

| DNS host | Domains (examples) | Action |
|----------|-------------------|--------|
| **A2** (`ns*.a2hosting.com`) | seehart, yknotlabs, agi.green, wondercamp | Transfer to Cloudflare at renewal |
| **GoDaddy** | gameofy.com (likely expired) | Renew or let lapse; if renew → transfer to Cloudflare |
| **Azure DNS** | evolver.ai | Work domain — out of scope |
| **Other** | nfnc.com | Migrate at renewal |

Ken-owned: seehart.com, agi.green, yknotlabs.com, wondercamp.site, carolegolden.com, nfnc.com, gameofy.com.

## Ownership config

Edit **`~/.config/ken/host/domains.yaml`** (template: [`templates/domains.yaml.example`](../templates/domains.yaml.example)).

```yaml
domains:
  - domain: example.com
    owner: ken
    registrar: cloudflare
    hosting: a2
    docroot: ~/example.com
    site_name: example
```

Jeff/shared domains: `owner: jeff` — inventory only unless coordinated.

## Inventory commands

```bash
sitehost inventory
sitehost inventory --columns domain,registrar,renewal,up,dns_host
sitehost inventory --json
```

MCP: `host_inventory(owner="ken", format="text|md|json", columns="domain,up,renewal")`

## Phase 2 MCP

`host_inventory` on Host MCP after Phase 2 deploys to `seehart.com/host/mcp`.
