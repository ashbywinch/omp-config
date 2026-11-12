# Adding an AI provider to the gateway

Goal: wire a new provider (BYOK — bring your own key) into a Cloudflare dynamic
route (`skill://cloudflare-ai-gateway`, "Dynamic routes").

## The one constraint that decides everything

**Dynamic-route model nodes call custom providers at the FORCED OpenAI path
`{origin}/v1/chat/completions`** — the base_url path is not used. Cloudflare
docs: "base_url should contain only the provider's root domain. Do not include
API path segments like /v1" (the gateway appends the path itself).

- Provider serves OpenAI chat completions at exactly `{origin}/v1/chat/completions`
  → a route node works directly.
- Provider path differs (z.ai — the GLM (General Language Model) Coding Plan
  provider: `/api/coding/paas/v4/chat/completions`; opencode-go — the OpenCode
  Zen Go gateway: `/zen/go/v1`).
- A provider whose path differs cannot be onboarded to a route. This is a
  selection criterion, not an engineering problem. Pick a provider that serves
  at the forced path. A provider that does not can still be reached outside the
  gateway: an aggregator for route traffic, or `skill://litellm-gateway`
  locally.
- Nothing sits between the gateway and the provider to rewrite a path.
  Cloudflare Workers cannot hold a streamed LLM answer open, so a path
  rewrite there is not available either.
The **provider-specific endpoint** (`.../{gateway}/custom-{slug}/<path>`)
appends everything after the slug to base_url, so it has full path control.
It does not run dynamic routes — no conditional, no fallback. Use it to validate a provider in isolation before touching a route.

## Validation sequence (cheapest first)

1. **Probe the provider directly** (curl, no auth). The response tells you
   whether the path exists. Auth errors (`401`, or a body like
   `{"error":{"code":"1001",...}}`) mean the path is real and behind an auth
   gate; nginx/Spring `404` means the path does not exist. Caveat: auth gates
   often answer ANY path under their prefix — a 401 does not prove the exact
   route exists.
2. **Probe again with the real key** and a model id from the catalog. A path
   that answers anonymously can still reject the key — an unauthorised key
   surfaces here, before the provider exists.
3. **Create the custom provider**: `POST /ai-gateway/custom-providers`
   `{name, slug, base_url}`.
4. **Add the BYOK key** via the dashboard Provider Keys (secret contract and
   dashboard-vs-API choice live in the Provider keys section of `SKILL.md`).
5. **Test the provider-specific endpoint** with the real model name in the
   body: `.../{gateway}/custom-{slug}/<path>`. This isolates key/base/model
   from route construction. Success here + failure in the route = the
   forced-path constraint, not your config.
6. **Read the gateway log** (`GET .../logs`). `byok` says whether the key
   attached. The `path` field is the client's remainder, not proof of the
   upstream URL, so a logged 200 does not show which path the provider served.

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
- `cf-aig-metadata`, the header carrying per-request metadata, takes one JSON
  object of at most five entries. Every value in it is a string, number or
  boolean; a nested object is rejected.

## Fail-back semantics (read before trusting a cascade)

- A model node's `fallback` output fires on non-2xx status or timeout.
- **200-with-error-body bypasses the cascade** — providers billed by
  subscription plan do this. Standard pay-per-token APIs return real status
  codes, which is one more reason the routes only carry them. Do not add a provider that returns
  errors as HTTP 200 to a route. The cascade will not fire.
- Failed intermediate nodes are NOT logged separately — logs show only the
  final serving provider. A missing log entry does not mean "not attempted".

## Cache

The gateway caches responses (`cache_ttl` on the gateway). A ~9ms response
that echoes an earlier prompt is a cache hit. Cache-bust tests with a random
token in the prompt.

## Non-standard-path providers (z.ai Coding Plan, OpenCode Zen)

The plans serve at their own paths and cannot join a route. A plan model can
also be listed on a standard-path aggregator (OpenRouter carries
`meta/muse-spark-1.3-contributor`, for example). Prefer the aggregator for
route traffic.

## Model ids and catalog drift (OpenCode Zen Go worked example)

- Custom-provider catalogs may use **bare model ids** (`deepseek-v4-flash`,
  `mimo-v2.5`) — vendor-prefixed ids (`deepseek/deepseek-v4-flash`) are
  rejected with `Model ... is not supported`. The catalog is public for
  OpenCode Zen Go: `GET {base}/v1/models`.
- `DataPolicyError` (OpenCode) = the model requires the workspace opt-in
  (e.g. muse-spark contributors).
- OpenCode Zen Go errors past the path fix: `MonthlyLimitError` (HTTP 401) —
  the workspace monthly spending cap. Raise the cap at
  `https://opencode.ai/workspace/<workspace>/billing`.

## z.ai specifics (the worked example)

- Coding Plan OpenAI-compatible endpoint:
  `https://api.z.ai/api/coding/paas/v4/chat/completions`. Only `glm-5.3` and
  `glm-5.3-flash` are callable on the plan.
- Error formats you will see. Auth errors: `{"error":{"code":"1001"|"1000",...}}`.
  Quota and permission errors: `{"code":1001,"msg":...,"success":false}` (HTTP
  200 on some paths). A service-side path miss: `{"code":500,"msg":"404
  NOT_FOUND"}`. Spring-shaped errors carry `{"timestamp":...,"path":...}`.
  Read that `path` as context-relative. It is not the upstream path.
- The Coding Plan is restricted to officially supported tools (Pi included);
  unsupported-tool traffic risks throttling, then account ban after 3
  violations. Requests should carry the harness identity the provider expects.
- Plan quota runs on 5-hour cycles plus a weekly cap; exhaustion returns
  "1113 Insufficient Balance" and does not cascade if delivered as HTTP 200.
