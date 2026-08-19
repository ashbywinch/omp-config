# Integrations — Paseo, Standalone OMP, PR-Agent

## Paseo Integration

### config.json

See `skill://cloudflare-ai-gateway/examples/paseo-config.json`. The model ID must be resolvable in OMP's model registry (see `models.yml` below).

### omp-yolo.sh

See `skill://cloudflare-ai-gateway/examples/omp-yolo.sh`. Sets `OPENAI_BASE_URL` to the proxy and tags the proxy with the repo name.

## Standalone OMP Integration

### config.yml

See `skill://cloudflare-ai-gateway/examples/config.yml` for the full file. Key points:

- `modelRoles` use the `cloudflare-gateway` provider with dynamic route names
- `retry.modelFallback` is `false` — the Cloudflare dynamic route handles failover
- `tier.openai` must be `auto`

### models.yml

See `skill://cloudflare-ai-gateway/examples/models.yml` for the full file. Key points:

- `baseUrl` points at the local proxy (`http://localhost:9123/v1`)
- `apiKey` reads from `CLOUDFLARE_AIGATEWAY_TOKEN` env var
- Two models: `dynamic/fallback2` (text) and `dynamic/image` (vision, supports images)

`tier.openai` must be `auto` (not `none` — that disables the OpenAI provider).

## PR-Agent Integration

PR-Agent runs in GitHub Actions and uses litellm (not the OpenAI SDK directly). Config goes in `.pr_agent.toml`:

### .pr_agent.toml

See `skill://new-repo-scaffold/examples/.pr_agent.toml` for the full template. The Cloudflare-specific section to add or modify:

```toml
[litellm]
extra_headers = '{"cf-aig-request-timeout": "1800000", "cf-aig-max-attempts": "0", "cf-aig-backoff": "exponential", "cf-aig-metadata": "{\"source\":\"review\",\"repo\":\"<project-name>\"}"}'
```

### GitHub workflow

See `skill://new-repo-scaffold/examples/.github/workflows/pr-agent.yml` for the full template. The Cloudflare-specific env vars to set:

```yaml
OPENAI_KEY: ${{ secrets.CLOUDFLARE_AIGATEWAY_TOKEN }}
OPENAI_BASE_URL: https://gateway.ai.cloudflare.com/v1/{ACCOUNT_ID}/{GATEWAY}/compat
PR_AGENT_CONFIG_BRANCH: pr-agent-config
```

### Security

- `.pr_agent.toml` MUST be loaded from a maintainer-controlled branch (`PR_AGENT_CONFIG_BRANCH`). Never from the PR head — an attacker could ship their own `api_base`.
- No `actions/checkout` in the review job — the working tree could contain a malicious `pyproject.toml` with `[tool.pr-agent]` overrides.
- The `cfut_` token is runtime-only; it can make inference calls but cannot manage gateway configuration.

## Rollback

```bash
bash ~/.paseo/rollback.sh
systemctl --user restart paseo
```

Restores: original `config.json`, `omp-yolo.sh`, `config.yml`, removes `models.yml`, restores `.zshrc`. Stops/disables proxy.