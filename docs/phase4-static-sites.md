# Phase 4 — additional static sites

Roll out the same CI pattern as [seehart](../seehart/) when each project has a `site/` tree and domain.

| Site | Repo | Status |
|------|------|--------|
| seehart | `seehart/` | Phase 1 — `deploy-seehart.yml` |
| Game of Y | `y/` | `deploy-gameofy.yml` → `yknotlabs.com` |
| nfnc | `nfnc/` | TBD — run `sitehost mkweb` when landing page domain is chosen |
| cristopoly | `cristopoly/` | TBD — static play sheet / landing when ready |

Shared GitHub secrets (`SSH_PRIVATE_KEY`, `HOST_SSH_USER`, `HOST_SSH_HOST`) work across repos on the same hosting.com account.

```bash
sitehost mkweb "NFNC" --domain example.com
sitehost setup-deploy --ssh-user CPANEL_USER --apply-gh
```
