# Integrations

## Paseo

- **config.json**: see `skill://cloudflare-ai-gateway/examples/paseo-config.json`
- **omp-yolo.sh**: see `skill://cloudflare-ai-gateway/examples/omp-yolo.sh`

## Standalone OMP

- **config.yml**: see `skill://cloudflare-ai-gateway/examples/config.yml`
- **models.yml**: see `skill://cloudflare-ai-gateway/examples/models.yml`
- `tier.openai` must be `auto` (not `none`)

## PR-Agent

- **`.pr_agent.toml`**: see `skill://new-repo-scaffold/examples/.pr_agent.toml` — the `[litellm]` section contains the Cloudflare timeout/retry/metadata headers
- **Workflow**: see `skill://new-repo-scaffold/examples/.github/workflows/pr-agent.yml` — set `OPENAI_KEY`, `OPENAI_BASE_URL`, `PR_AGENT_CONFIG_BRANCH`
- `.pr_agent.toml` MUST be loaded from a maintainer-controlled branch (`PR_AGENT_CONFIG_BRANCH`)
- No `actions/checkout` in the review job — an attacker could ship a malicious `pyproject.toml`
- The `cfut_` token is runtime-only; it can't manage gateway configuration

## Rollback

```bash
bash ~/.paseo/rollback.sh
systemctl --user restart paseo
```