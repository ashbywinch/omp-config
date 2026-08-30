---
name: cloudflare-ai-gateway
description: Cloudflare AI Gateway configuration for Paseo/OMP — setup, proxy service, PR-Agent integration, troubleshooting
---

# Cloudflare AI Gateway

Routes all AI API calls through Cloudflare AI Gateway. The `fallback2` route is purpose-gated: harness traffic (via the local proxy) tries z.ai GLM-5.3-Flash first, then cascades to DeepSeek; all other traffic (evals, apps, review bot) goes straight to the DeepSeek cascade. Per-repo analytics tagging via local proxy. The canonical LLM provider config for all projects.

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
      z.ai GLM-5.3-Flash        DeepSeek cascade
      (harness only, via shim)  (opencode-go → deepseek)
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

#### Purpose-gated topology (`fallback2`)

`fallback2` starts with a conditional on `metadata.purpose == "harness"`:

- **true (harness)**: z.ai GLM-5.3-Flash (`custom-zai`, via shim) → fallback → opencode-go → fallback → deepseek
- **false (evals, apps, review bot)**: opencode-go → deepseek — never touches z.ai
- `dynamic/image` (vision): opencode-go `mimo-v2.5` → fallback → openrouter `xiaomi/mimo-v2.5`

Only the local proxy stamps `purpose: "harness"`; PR-Agent sends `source: "review"`; untagged direct traffic has no purpose. The shims live in `tools/ai-gateway-shims/` (`deploy.sh` deploys both). Adding providers — the forced `/v1/chat/completions` route-node constraint, validation sequence, shim pattern, fail-back caveats — see `references/adding-providers.md`.

## Timeouts and retries

### What we know

**Model node timeout** — the Cloudflare dynamic route's model node has a single `timeout` property. The docs say "Request timeout in milliseconds". We observed a 504 at 31s when the timeout was 30s. Current route values are visible via the routes API (see Cloudflare Dashboard section above) — don't hardcode them here.

**`cf-aig-request-timeout` header** — documented as first-byte timeout ("If the first part of the response arrives within this window, the gateway will wait"). We confirmed the gateway recognizes it (14s test returned 200).

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

The local proxy adds these headers to every request. PR-Agent in GitHub Actions needs them sent via `[litellm] extra_headers` in `.pr_agent.toml` — as a JSON **string**: the handler runs `json.loads(get_settings().litellm.extra_headers)`, so an inline TOML table fails every call with "the JSON object must be str, bytes or bytearray, not DynaBox". The working block lives in the sample: `skill://new-repo-scaffold/examples/.pr_agent.toml` (the `[litellm]` section).

## Why the local proxy exists

The proxy exists for two reasons:

1. **Per-repo analytics tagging + purpose gating** — the proxy reads the repo name (tagged by `omp-yolo.sh`) and injects `cf-aig-metadata: {"source":"agent","purpose":"harness","repo":"<name>"}`. `purpose: "harness"` selects the z.ai branch of `fallback2`; direct traffic has no purpose and keeps the DeepSeek cascade. Without the proxy, every request would show as coming from "unknown".

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
