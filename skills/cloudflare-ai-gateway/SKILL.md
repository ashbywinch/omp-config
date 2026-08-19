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
          │  Account: {ACCOUNT_ID} (from dashboard) │
          │  Gateway: {GATEWAY} (usually default)   │
          │  Auth: CLOUDFLARE_AIGATEWAY_TOKEN       │
          └────────────────┬────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      OpenCode (primary)      DeepSeek (fallback)
      (out of credits → fail)  (funded)
```

### Two env vars — single source of truth

The convention is `OPENAI_BASE_URL` + `OPENAI_API_KEY`. PR-Agent is an exception: it reads `OPENAI_KEY` (the OpenAI Python SDK env var, not the litellm one). The workflow env sets `OPENAI_KEY` for PR-Agent; all other clients use `OPENAI_API_KEY`.

| Env var | Purpose | Set where |
|---|---|---|
| `OPENAI_BASE_URL` | Cloudflare compat endpoint | `.zshrc`, `omp-yolo.sh`, GitHub secrets |
| `OPENAI_API_KEY` | Gateway auth token | shell environment (`.zshrc`, GitHub secrets) |

The current values (account ID, gateway name are in Cloudflare — query them):

```dotenv
OPENAI_BASE_URL=https://gateway.ai.cloudflare.com/v1/{ACCOUNT_ID}/{GATEWAY}/compat
OPENAI_API_KEY=                            # value from CLOUDFLARE_AIGATEWAY_TOKEN env var
```

**For forkers**: change these two values. That's it. Every tool reads them.

### Model names

The model name in the request body selects the Cloudflare dynamic route — `dynamic/{route-name}`. Routes are configured in the Cloudflare dashboard (see above). Convention:

| Use case | Route naming | Suggested model |
|---|---|---|
| Text (default) | `{name}-text` or `{name}` | `dynamic/fallback2` |
| Vision/images | `{name}-vision` or `{name}` | `dynamic/image` |

PR-Agent uses `openai/dynamic/fallback2` (the `openai/` prefix is stripped by the handler). Other clients send the model name as-is.

## Cloudflare Dashboard

### Gateway

Gateway settings are source-of-truth in Cloudflare — query them, don't hardcode:

- **Account ID**: from the dashboard URL `https://dash.cloudflare.com/{account_id}/ai/ai-gateway`
- **Gateway name**: from the dashboard (or the `default` auto-created gateway)
- **Compat endpoint**: `https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway}/compat`

### Dynamic routes

Routes, providers, model names, and timeouts are configured in Dashboard → AI → AI Gateway → `{gateway}` → Dynamic Routing. Query the current state via the admin API (see `skill://cloudflare-ai-gateway-analytics` for auth):

```bash
# List routes (returns current model nodes, providers, timeouts, retries)
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/routes" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"
```

Route names are referenced in config as `dynamic/{route-name}`. If a route is renamed in the dashboard, config files referencing the old name break — always verify against the API above.

### Provider keys

Stored in Dashboard → AI → AI Gateway → `{gateway}` → Provider Keys. Uses BYOK (Bring Your Own Key). Provider slugs are visible in the API route listing above (`custom-*` prefix for custom providers).

## Timeouts and retries

### What we know

**Model node timeout** — the Cloudflare dynamic route's model node has a single `timeout` property. The docs say "Request timeout in milliseconds". We observed a 504 at 31s when the timeout was 30s. Current route values are visible via the routes API (see Cloudflare Dashboard section above) — don't hardcode them here.

**`cf-aig-request-timeout` header** — documented as first-byte timeout ("If the first part of the response arrives within this window, the gateway will wait"). We confirmed the gateway recognizes it (14s test returned 200).

**Workers 100s limit** — **disproven**. The review ran for 10 minutes through the gateway without issue. The earlier 504s were from the model node timeout, not a Worker ceiling.

### What we're uncertain about

Whether the model node `timeout` is:
- **Timeout to first byte** — DeepSeek took >30s to produce the first token on a cold start with a 32K-token prompt, and the stream then continued for ~5 minutes of inference.
- **Total request timeout** — DeepSeek completed the full response, and the timeout covers the total duration including streaming.

Both are consistent with the evidence. The 300s timeout works either way.

### Retries

Cloudflare's model node retries ALL errors — it can't distinguish between:
- **Non-retryable**: 402 billing, 401 auth, 400 invalid request, 404 model not found (retrying wastes time)
- **Retryable**: 429 rate limit, 500/502/503 transient, 529 overloaded, timeouts (retrying helps)

**Decision (2026-08-19): Cloudflare-side retries are DISABLED (`retries: 0` on model nodes, `cf-aig-max-attempts: 0` header). The client owns retries.**

Rationale:
- A review timing out will fail again on retry — the same large diff, the same cost. Retrying at the gateway wastes tokens.
- A transient provider error IS worth retrying, and the client (PR-Agent, Paseo/OMP) does that with full context about whether it's a long-running review or a genuine error.
- The client can distinguish "this is a complex request that needs more time" (no retry, wait longer) from "the provider errored" (retry). The gateway cannot.

Cloudflare's model node retries on all errors equally, so it would waste attempts on both non-retryable errors AND on long-running reviews that simply need more time.

**The timeout ambiguity problem** — it's a known industry issue (see A Field Guide to LLM API Error Messages, Multigrid). A timeout can mean either:
- The provider is broken (should retry/failover)
- The request is complex and needs more time (should wait longer)

Solutions other gateways use:
- **LiteLLM**: separate `timeout` (total) and `stream_timeout` (first-byte) settings
- **AISIX APISIX**: inspects response body to classify error types before retrying
- **Portkey, others**: similar pattern — classify by status code + error message body

Cloudflare's model node has a single `timeout` and retries on all errors. For our use case:
- Primary (OpenCode, out of credits): 2 retries at 120s timeout — errors are instant, so retries are fast
- Fallback (DeepSeek): 2 retries at 300s timeout — gives enough time for complex requests

### cf-aig-* headers

Per-request headers that override the model node's settings:

| Header | Purpose |
|---|---|
| `cf-aig-request-timeout` | Upstream timeout in ms. **First-byte timeout** (docs: "If the first part of the response arrives within this window, the gateway will wait"). |
| `cf-aig-max-attempts` | Max retries (0-5) |
| `cf-aig-retry-delay` | Delay between retries (ms, max 5000) |
| `cf-aig-backoff` | `constant`, `linear`, or `exponential` |

The local proxy adds these headers to every request. PR-Agent in GitHub Actions needs them sent via `[litellm] extra_headers` in `.pr_agent.toml` (see below).

### Worker 100s limit

**Hypothesis**: Cloudflare Workers have a ~100s execution limit (documented in community posts). The AI Gateway runs on Workers, so long-running streams might hit this ceiling. The 504s at ~94s during PR-Agent runs are consistent with this limit. The `cf-aig-request-timeout` header might override this, but we haven't confirmed. If long reviews still fail after the route timeout increase, the Worker limit is the likely cause. Workaround: route PR-Agent directly to DeepSeek (bypass gateway) or upgrade to Enterprise.

## Why the local proxy exists

The proxy exists for two reasons:

1. **Per-repo analytics tagging** — the proxy reads the repo name (tagged by `omp-yolo.sh`) and injects `cf-aig-metadata: {"source":"agent","repo":"<name>"}`. This lets Cloudflare's analytics show per-repo token usage, cost, and request patterns. Without the proxy, every request would show as coming from "unknown".

2. **Timeout/retry header injection** — the proxy adds `cf-aig-request-timeout`, `cf-aig-max-attempts`, and `cf-aig-backoff` headers to every forwarded request. The PR-Agent in GitHub Actions needs these headers set via `[litellm] extra_headers` in `.pr_agent.toml` (which we confirmed works). The proxy covers local OMP sessions.

The proxy is NOT needed for:
- Provider failover (handled by Cloudflare's dynamic route)
- Authentication (handled by `OPENAI_API_KEY` / `CLOUDFLARE_AIGATEWAY_TOKEN`)
- Model routing (handled by the model name in the request body)

## Local Metadata Proxy

### What it does

A Bun script (`cf-proxy.ts`) running as a systemd user service. It:
1. Receives requests from OMP on `localhost:9123`
2. Reads the repo name (tagged by `omp-yolo.sh`)
3. Adds `cf-aig-metadata: {"source":"agent","repo":"<name>"}` header
4. Adds timeout/retry headers (values from `cf-aig-request-timeout` config)
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
| `~/.paseo/cf-proxy.ts` | Proxy source (Bun) |
| `~/.config/systemd/user/cf-gateway-proxy.service` | Systemd unit |

## Paseo Integration

### config.json

See `skill://cloudflare-ai-gateway/examples/paseo-config.json`. The model ID must be resolvable in OMP's model registry (see `models.yml` above).

### omp-yolo.sh

See `skill://cloudflare-ai-gateway/examples/omp-yolo.sh`. Sets `OPENAI_BASE_URL` to the proxy and tags the proxy with the repo name.

## Standalone OMP Integration

### config.yml

See `skill://cloudflare-ai-gateway/examples/config.yml` for the full file. Key points:

- `modelRoles` use the `cloudflare-gateway` provider with dynamic route names
- `retry.modelFallback` is `false` — the Cloudflare dynamic route handles failover
- `tier.openai` must be `auto`

### models.yml

Custom provider registered in OMP's model registry. See `skill://cloudflare-ai-gateway/examples/models.yml` for the full file. Key points:

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
extra_headers = '{"cf-aig-request-timeout": "600000", "cf-aig-max-attempts": "0", "cf-aig-backoff": "exponential", "cf-aig-metadata": "{\"source\":\"review\",\"repo\":\"<project-name>\"}"}'
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

## Troubleshooting

### 504 Gateway Timeout

**Observed**: PR-Agent review runs returned 504 at ~94s. Local curl through the gateway returned 504 at ~31s (when fallback timeout was 30s).

**Root cause**: The model node timeout was too short. DeepSeek needed more time than the route's timeout allowed. Query the current route timeouts via the routes API (see Cloudflare Dashboard section above).

**Workers 100s limit disproven**: The review ran for 10 minutes through the gateway without issue. The AI Gateway does not inherit the Workers 100s execution limit.

**Fix applied**: Increased the model node timeout to accommodate long reviews. Current values are queryable via the routes API.

**If 504s persist**: Route PR-Agent directly to DeepSeek by setting `OPENAI_BASE_URL` to `https://api.deepseek.com/v1` and `OPENAI_KEY` to the `DEEPSEEK_API_KEY` env var value.

### 502 / "Failed to get response from provider"

- Check proxy running: `systemctl --user is-active cf-gateway-proxy.service`
- Test gateway directly: `curl -s "$OPENAI_BASE_URL/v1/chat/completions" -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_TOKEN" -H "Content-Type: application/json" -d '{"model":"dynamic/fallback2","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check DeepSeek has credits: `curl -s "https://api.deepseek.com/v1/chat/completions" -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check the provider API key is set in the environment (e.g. `CLOUDFLARE_AIGATEWAY_TOKEN` in the shell profile)

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
- Expect `PATCH` on a route to update its elements — it only renames the route. Creating a new version (`POST .../versions`) and deploying it (`POST .../deployments`) is the correct way to update timeouts and model nodes.
- Assume the model node `timeout` is first-byte or last-byte — set it generously (~300s) to cover both cases.
- Set `tier.openai = none` (disables the OpenAI provider entirely)
- Skip the `pr-agent-config` branch pin — any PR branch could ship its own `api_base`
- Forget `make install` + restart omp after editing this skill — changes are not live until installed
- Set `tier.openai = none` (disables the OpenAI provider entirely)
- Skip the `pr-agent-config` branch pin — any PR branch could ship its own `api_base`