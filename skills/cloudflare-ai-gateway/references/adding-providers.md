# Adding an AI provider to the gateway

Goal: wire a new provider (BYOK) into a Cloudflare dynamic route with the least
trial-and-error. These lessons are empirical (2026-08-30, z.ai GLM Coding Plan
integration) — they exist so a future agent does not re-derive them.

## The one constraint that decides everything

**Dynamic-route model nodes call custom providers at the FORCED OpenAI path
`{origin}/v1/chat/completions`** — the base_url path is not used. Cloudflare
docs: "base_url should contain only the provider's root domain. Do not include
API path segments like /v1" (the gateway appends the path itself).

- Provider serves OpenAI chat completions at exactly `{origin}/v1/chat/completions`
  → a route node works directly.
- Provider path differs (z.ai: `/api/coding/paas/v4/chat/completions`;
  opencode-go: `/zen/go/v1`) → the provider CANNOT be onboarded to a route.
  This is a selection criterion, not an engineering problem: pick a
  provider that serves at the forced path, or reach the non-standard one
  outside the gateway (the LiteLLM local chain calls them natively).
The **provider-specific endpoint** (`.../{gateway}/custom-{slug}/<path>`) appends
everything after the slug to base_url — full path control — but does NOT run
dynamic routes (no conditional, no fallback). Use it to validate a provider in
isolation before touching a route.

## Validation sequence (cheapest first)

1. **Probe the provider directly** (curl, no auth) — the response tells you
   whether the path exists. Auth errors (`401`, or a body like
   `{"error":{"code":"1001",...}}`) mean the path is real and behind an auth
   gate; nginx/Spring `404` means the path does not exist. Caveat: auth gates
   often answer ANY path under their prefix — a 401 does not prove the exact
   route exists.
2. **Create the custom provider**: `POST /ai-gateway/custom-providers`
   `{name, slug, base_url}`.
3. **Add the BYOK key** via the dashboard Provider Keys (secret contract and
   dashboard-vs-API choice live in the Provider keys section of `SKILL.md`).
4. **Test the provider-specific endpoint** with the real model name in the
   body: `.../{gateway}/custom-{slug}/<path>`. This isolates key/base/model
   from route construction. Success here + failure in the route = the
   forced-path constraint, not your config.
5. **Read the gateway log** (`GET .../logs`): `path` = the exact upstream path
   the gateway used; `byok` = whether the key attached. Log `path` is the
   client remainder, not proof of the final upstream URL.

## Route mechanics

- Routes are versioned flows: `POST /routes/{id}/versions` `{elements}` →
  draft; `POST /routes/{id}/deployments` `{version_id}` → live. Old versions
  remain → instant rollback by redeploying an older `version_id`.
- Response shapes: routes list = `data.routes[]`; versions list =
  `data.versions[]` (not `result`).
- Elements: `start` → `conditional` (conditions like
  `{"metadata.<key>": {"$eq": "<val>"}}`, outputs `true`/`false`) → `model`
  (`provider`, `model`, `timeout`, `retries`; outputs `success`/`fallback`)
  → `end`.
- `cf-aig-metadata` values must be strings/numbers/booleans, max 5 entries;
  objects are rejected.

## Fail-back semantics (read before trusting a cascade)

- A model node's `fallback` output fires on non-2xx status or timeout. Proven:
  z.ai returning 404 → cascade → deepseek served.
- **200-with-error-body bypasses the cascade** — a plan-provider pathology.
  Standard pay-per-token APIs return real status codes, which is one more
  reason the routes only carry them.
- Failed intermediate nodes are NOT logged separately — logs show only the
  final serving provider. A missing log entry does not mean "not attempted".

## Cache

The gateway caches responses (`cache_ttl` on the gateway). A ~9ms response
that echoes an earlier prompt is a cache hit — cache-bust tests with a random
token in the prompt.

## Non-standard-path providers (z.ai Coding Plan, OpenCode Zen)

The plans serve at their own paths and cannot join a route. They still have
value: the LiteLLM local chain (`'/home/ashby/.omp/agent/skills/litellm-gateway'`) calls them
natively — LiteLLM sets the full URL, no forced path. If a plan model is
also listed on a standard-path aggregator (e.g. OpenRouter carries
`meta/muse-spark-1.3-contributor`), prefer the aggregator for route traffic
and keep the plan for local traffic.

## Model ids and catalog drift (OpenCode Zen Go worked example)

- Custom-provider catalogs may use **bare model ids** (`deepseek-v4-flash`,
  `mimo-v2.5`) — vendor-prefixed ids (`deepseek/deepseek-v4-flash`) are
  rejected with `Model ... is not supported`. Check the catalog:
  `GET {base}/v1/models` is public for OpenCode Zen Go.
- `DataPolicyError` (OpenCode) = the model requires the workspace opt-in
  (e.g. muse-spark contributors).
- OpenCode Zen Go errors past the path fix: `MonthlyLimitError` (HTTP 401) —
  the workspace monthly spending cap. Raise the cap at
  `https://opencode.ai/workspace/<workspace>/billing`.

## z.ai specifics (the worked example)

- Coding Plan OpenAI-compatible endpoint:
  `https://api.z.ai/api/coding/paas/v4/chat/completions`. Only `glm-5.3` and
  `glm-5.3-flash` are callable on the plan.
- Error formats you will see: auth `{"error":{"code":"1001"|"1000",...}}`;
  `{"code":1001,"msg":...,"success":false}` (HTTP 200 on some paths);
  `{"code":500,"msg":"404 NOT_FOUND"}` (a path missing inside their service);
  Spring `{"timestamp":...,"path":"/v1/chat/completions"}` — that `path` is
  context-relative, not the upstream path; do not misread it.
- The Coding Plan is restricted to officially supported tools (Pi included);
  unsupported-tool traffic risks throttling, then account ban after 3
  violations. Requests should carry the harness identity the provider expects.
- Plan quota runs on 5-hour cycles plus a weekly cap; exhaustion returns
  "1113 Insufficient Balance" and does not cascade if delivered as HTTP 200.
