---
name: cloudflare-ai-gateway
description: Cloudflare AI Gateway configuration for Paseo/OMP — setup, proxy service, PR-Agent integration, troubleshooting
---

# Cloudflare AI Gateway

Routes all AI API calls through Cloudflare AI Gateway with OpenCode (primary) → DeepSeek (fallback). Per-repo analytics tagging via local proxy. The canonical LLM provider config for all projects.

## Architecture

### Call flow

```
                    ┌─ Paseo ──→ omp-yolo.sh ──┐
                    │                          │
                    │  standalone OMP          │
                    │  (config.yml models.yml) │
                    │                          ▼
                    │              ┌──────────────────────┐
                    │              │  local proxy (:9123) │
                    │              │  systemd service     │
                    │              │  adds cf-aig-*       │
                    │              │  headers             │
                    │              └──────────┬───────────┘
                    │                         │
                    │  PR-Agent (GitHub         │
                    │  Actions) ───────────────┤
                    │                          │
                    ▼                          ▼
          ┌─────────────────────────────────────────┐
          │  Cloudflare AI Gateway                  │
          │  Account: e21a5be58ac1e8f7d5619539feb2dc3d  │
          │  Gateway: default                       │
          │  Auth: CLOUDFLARE_AIGATEWAY_TOKEN       │
          └────────────────┬────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      OpenCode (primary)      DeepSeek (fallback)
      (out of credits → fail)  (funded)
```

### Two env vars — single source of truth

Every environment reads LLM provider config from the same two env vars:

| Env var | Purpose | Set where |
|---|---|---|
| `OPENAI_BASE_URL` | Cloudflare compat endpoint | `.zshrc`, `omp-yolo.sh`, GitHub secrets |
| `OPENAI_API_KEY` | Gateway auth token | `.secrets`, GitHub secrets |

The current values:

```dotenv
OPENAI_BASE_URL=https://gateway.ai.cloudflare.com/v1/e21a5be58ac1e8f7d5619539feb2dc3d/default/compat
OPENAI_API_KEY=                            # value from CLOUDFLARE_AIGATEWAY_TOKEN env var
```

**For forkers**: change these two values. That's it. Every tool reads them.

### Model names

The model name in the request body selects the Cloudflare dynamic route:

| Use case | Model name | Route | Fallback |
|---|---|---|---|
| Text (default) | `dynamic/fallback2` | OpenCode → DeepSeek | DeepSeek-direct |
| Vision/images | `dynamic/image` | OpenCode → Mimo | Configurable in dashboard |

PR-Agent uses `openai/dynamic/fallback2` (the `openai/` prefix is stripped by the handler). Other clients send the model name as-is.

## Cloudflare Dashboard

### Gateway

- **Account ID**: `e21a5be58ac1e8f7d5619539feb2dc3d`
- **Gateway name**: `default`
- **Compat endpoint**: `https://gateway.ai.cloudflare.com/v1/{account_id}/default/compat`

### Dynamic routes

Created in Dashboard → AI → AI Gateway → `default` → Dynamic Routing.

| Route | Primary provider | Fallback provider | Model name |
|---|---|---|---|
| `fallback2` | OpenCode (OpenRouter) | DeepSeek-direct | `dynamic/fallback2` |
| `image` | OpenCode (OpenRouter) | (configured) | `dynamic/image` |

### Provider keys

Stored in Dashboard → AI → AI Gateway → `default` → Provider Keys. Uses BYOK (Bring Your Own Key). Key names: `custom-openrouter`, `custom-deepseek`, etc.

### Timeout configuration

The `cf-aig-request-timeout` header (milliseconds) controls the upstream timeout. The `cf-aig-max-attempts` header controls retries (0-5). Set these per-request — see the PR-Agent section below for how.

## Local Metadata Proxy

### What it does

A Bun script (`cf-proxy.ts`) running as a systemd user service. It:
1. Receives requests from OMP on `localhost:9123`
2. Reads the repo name (tagged by `omp-yolo.sh`)
3. Adds `cf-aig-metadata: {"source":"agent","repo":"<name>"}` header
4. Adds timeout/retry headers (`cf-aig-request-timeout: 300000`, etc.)
5. Forwards to Cloudflare

### Service management

```bash
systemctl --user status cf-gateway-proxy.service     # check status
systemctl --user restart cf-gateway-proxy.service    # restart after code change
journalctl --user -u cf-gateway-proxy.service -n 50  # view logs
systemctl --user enable cf-gateway-proxy.service     # survive reboots
```

Health check: `curl http://localhost:9123/health` → `ok`

### Files

| Path | Purpose |
|---|---|
| `/home/ashby/.paseo/cf-proxy.ts` | Proxy source (Bun) |
| `/home/ashby/.config/systemd/user/cf-gateway-proxy.service` | Systemd unit |

## Paseo Integration

### config.json

The Paseo daemon passes the model to OMP. The model ID must be resolvable in OMP's model registry (see `models.yml` below).

```json
{
  "models": [{
    "id": "cloudflare-gateway/dynamic/fallback2",
    "label": "DeepSeek V4 Flash (via Cloudflare)",
    "isDefault": true
  }]
}
```

### omp-yolo.sh

The launcher script sets env vars and tags the proxy with the repo name:

```bash
export OPENAI_BASE_URL="http://localhost:9123/v1"
export OPENAI_API_KEY="$CLOUDFLARE_AIGATEWAY_TOKEN"
```

## Standalone OMP Integration

### config.yml

Model roles select which Cloudflare dynamic route to use:

```yaml
modelRoles:
  default: cloudflare-gateway/dynamic/fallback2   # text
  advisor: cloudflare-gateway/dynamic/fallback2
  designer: cloudflare-gateway/dynamic/image       # vision
  vision: cloudflare-gateway/dynamic/image
```

### models.yml

Custom provider registered in OMP's model registry. The `cloudflare-gateway` provider points at the local proxy with its own `apiKey`:

```yaml
providers:
  cloudflare-gateway:
    baseUrl: http://localhost:9123/v1
    apiKey: CLOUDFLARE_AIGATEWAY_TOKEN
    api: openai-completions
    models:
      - id: dynamic/fallback2
        name: DeepSeek V4 Flash (via Cloudflare)
        contextWindow: 1000000
        maxTokens: 128000
      - id: dynamic/image
        name: Mimo V2.5 Vision (via Cloudflare)
        contextWindow: 1000000
        maxTokens: 128000
        input: [text, image]
```

Settings: `tier.openai = auto` (not `none` — that disables OpenAI provider).

## PR-Agent Integration

PR-Agent runs in GitHub Actions and uses litellm (not the OpenAI SDK directly). Config goes in `.pr_agent.toml`:

### .pr_agent.toml

```toml
[openai]
custom_llm_provider = "openai"
api_base = "https://gateway.ai.cloudflare.com/v1/e21a5be58ac1e8f7d5619539feb2dc3d/default/compat"

[config]
model = "openai/dynamic/fallback2"    # openai/ prefix is stripped before sending
custom_model_max_tokens = 128000
max_model_tokens = 128000
ai_timeout = 300                       # client-side timeout (seconds)

[litellm]
# Cloudflare timeout/retry headers — sent as HTTP headers to the gateway.
# 5 min timeout, 5 retries with exponential backoff.
extra_headers = '{"cf-aig-request-timeout": "300000", "cf-aig-max-attempts": "5", "cf-aig-backoff": "exponential"}'
```

### GitHub workflow

```yaml
steps:
  - uses: the-pr-agent/pr-agent@<pinned-sha>
    env:
      OPENAI_KEY: ${{ secrets.CLOUDFLARE_AIGATEWAY_TOKEN }}
      OPENAI_BASE_URL: https://gateway.ai.cloudflare.com/v1/e21a5be58ac1e8f7d5619539feb2dc3d/default/compat
      PR_AGENT_CONFIG_BRANCH: pr-agent-config
```

### Security

- `.pr_agent.toml` MUST be loaded from a maintainer-controlled branch (`PR_AGENT_CONFIG_BRANCH`). Never from the PR head — an attacker could ship their own `api_base`.
- No `actions/checkout` in the review job — the working tree could contain a malicious `pyproject.toml` with `[tool.pr-agent]` overrides.
- The `cfut_` token is runtime-only; it can make inference calls but cannot manage gateway configuration.

## Rollback

```bash
bash /home/ashby/.paseo/rollback.sh
systemctl --user restart paseo
```

Restores: original `config.json`, `omp-yolo.sh`, `config.yml`, removes `models.yml`, restores `.zshrc`. Stops/disables proxy.

## Troubleshooting

### 504 Gateway Timeout on PR-Agent

The upstream DeepSeek call is slow, especially on cold starts. Fixed by:
1. `[litellm] extra_headers` in `.pr_agent.toml` with `cf-aig-request-timeout: 300000` and `cf-aig-max-attempts: 5`
2. `ai_timeout = 300` in `[config]` (client-side timeout must match or exceed the Cloudflare timeout)

### 502 / "Failed to get response from provider"

- Check proxy running: `systemctl --user is-active cf-gateway-proxy.service`
- Test gateway directly: `curl -s "$OPENAI_BASE_URL/v1/chat/completions" -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_TOKEN" -H "Content-Type: application/json" -d '{"model":"dynamic/fallback2","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check DeepSeek has credits: `curl -s "https://api.deepseek.com/v1/chat/completions" -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check `.secrets` sourced in `start.sh`: `source /home/ashby/.secrets`

### "Model not found" / Falls back to Opus 4.8

OMP's model registry doesn't have the Cloudflare dynamic route names. Fix:
1. `models.yml` must define the `cloudflare-gateway` provider with the model IDs
2. `tier.openai` must be `auto` (not `none`)
3. `modelRoles` in `config.yml` must use `cloudflare-gateway/dynamic/...`

### Proxy not starting at boot

- `systemctl --user is-enabled cf-gateway-proxy.service` — must be `enabled`
- `loginctl show-user ashby | grep Linger` — must be `yes` for user services at boot

### "Incorrect API key provided: sk-..."

Check `PR_AGENT_CONFIG_BRANCH` pin first, not the key. Without the pin, the image defaults run (model `gpt-5.6`, `api_base api.openai.com`) and reject the key.

## Never do

- Delete/overwrite `cf-proxy.ts` without creating a systemd service replacement
- Expose `CLOUDFLARE_AIGATEWAY_TOKEN` in logs, code, or docs
- Use `OPENAI_CUSTOM_HEADERS` env var for PR-Agent headers — it's only read by the OpenAI Python SDK, not by litellm
- Set `tier.openai = none` (disables the OpenAI provider entirely)
- Skip the `pr-agent-config` branch pin — any PR branch could ship its own `api_base`