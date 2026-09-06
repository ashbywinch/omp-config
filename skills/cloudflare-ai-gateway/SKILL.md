---
name: cloudflare-ai-gateway
description: Cloudflare AI Gateway configuration for Paseo/OMP — setup, proxy service, PR-Agent integration, troubleshooting
---

# Cloudflare AI Gateway

Routes AI API calls for remote clients (PR-Agent, evals, apps) through Cloudflare AI Gateway. Every provider on a route serves at the forced `/v1/chat/completions` path — there is no rewriting layer. `fallback2` (text): Muse Spark 1.3 contributor (OpenRouter) → DeepSeek V4 Flash (OpenRouter) → DeepSeek direct. `image` (vision): z-ai/glm-4.6v (OpenRouter). The text default for omp/Paseo agents runs through the LiteLLM local chain (`skill://litellm-gateway`), which serves the z.ai Coding Plan and OpenCode Zen natively; Cloudflare serves PR-Agent (GitHub Actions cannot reach localhost), vision, and evals/apps, and stays configured as the manual rollback. Per-repo analytics tagging via local proxy.

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
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
   fallback2 (text): Muse Spark 1.3 →       image (vision):
   DeepSeek V4 Flash (OpenRouter) →         z-ai/glm-4.6v
   DeepSeek direct                          (OpenRouter)
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

Stored in Dashboard → AI → AI Gateway → `{gateway}` → Provider Keys. Uses BYOK (Bring Your Own Key). Provider slugs are visible in the API route listing above (`custom-*` prefix for custom providers). Adding a key via the dashboard creates the Secrets Store secret `{gateway}_{slug}_{alias}` automatically; the API path needs Secrets Store Write plus a pre-created secret — use the dashboard unless you hold that scope.

#### Route topology (all providers standard-path)

Every provider on a route must serve at the forced `/v1/chat/completions`
path — it is an onboarding criterion, not an engineering problem. A
provider whose endpoint differs is not added to a route.

- `fallback2` (text): openrouter `meta/muse-spark-1.3-contributor`
  ($0.10/$0.20 per M) → openrouter `deepseek/deepseek-v4-flash` →
  deepseek direct `deepseek-v4-flash`
- `image` (vision): openrouter `z-ai/glm-4.6v`

The former purpose-gating conditional and its path-rewrite Workers are
gone: the z.ai Coding Plan and OpenCode Zen serve local harness traffic
directly through LiteLLM (`skill://litellm-gateway`), which has no forced
path. Route changes are versioned — redeploy an older `version_id` to
roll back (versions preceding 2026-09-06 are the shim-era cascades).

## Timeouts and retries

### What we know

**Model node timeout** — the Cloudflare dynamic route's model node has a single `timeout` property. The docs say "Request timeout in milliseconds". We observed a 504 at 31s when the timeout was 30s. Current route values are visible via the routes API (see Cloudflare Dashboard section above) — don't hardcode them here.

**`cf-aig-request-timeout` header** — documented as first-byte timeout ("If the first part of the response arrives within this window, the gateway will wait"). We confirmed the gateway recognizes it (14s test returned 200).


### cf-aig-* headers

Per-request headers that override the model node's settings:

| Header | Purpose |
|---|---|
| `cf-aig-request-timeout` | Upstream timeout in ms. **First-byte timeout** (docs: "If the first part of the response arrives within this window, the gateway will wait"). |
| `cf-aig-max-attempts` | Max retries (0-5) |
| `cf-aig-retry-delay` | Delay between retries (ms, max 5000) |
| `cf-aig-backoff` | `constant`, `linear`, or `exponential` |

The local proxy adds these headers to every request. PR-Agent in GitHub Actions needs them sent via `[litellm] extra_headers` in `.pr_agent.toml` — as a JSON **string**: the handler runs `json.loads(get_settings().litellm.extra_headers)`, so an inline TOML table fails every call with "the JSON object must be str, bytes or bytearray, not DynaBox". The working block lives in the sample: `skill://new-repo-scaffold/examples/.pr_agent.toml` (the `[litellm]` section).

## Why the local proxy exists

The proxy exists for two reasons:

1. **Per-repo analytics tagging** — the proxy reads the repo name (tagged
   by `omp-yolo.sh`) and injects `cf-aig-metadata: {"source":"agent","purpose":"harness","repo":"<name>"}`. Without the proxy, every request
   would show as coming from "unknown". (The purpose field no longer
   selects a route branch — routes are unconditional cascades.)

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
3. Adds `cf-aig-metadata: {"source":"agent","purpose":"harness","repo":"<name>"}` header
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

## Integrations

See `references/integrations.md` — Paseo, OMP, and PR-Agent setup.

## Troubleshooting

See `references/troubleshooting.md` — common issues and fixes.
