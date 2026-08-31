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
  opencode-go: `/zen/go/v1`) → a route node CANNOT reach it. The `custom-*`
  node is not a path — you need a path-rewrite shim (below). This is why
  custom-opencode-go never served through routes despite having a valid key.

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
  z.ai returning 404 → cascade → deepseek served. (The shims also remap
  providers' HTTP-200 business errors to 502 for exactly this reason — see
  the shim pattern above.)
- **Uncorrected 200-with-error-body still bypasses the cascade** for any
  provider called without a shim. z.ai returns 200-with-error-body on some of
  its paths; a cascade is only as good as the status codes the provider
  actually sends.
- Failed intermediate nodes are NOT logged separately — logs show only the
  final serving provider. A missing log entry does not mean "not attempted".

## Cache

The gateway caches responses (`cache_ttl` on the gateway). A ~9ms response
that echoes an earlier prompt is a cache hit — cache-bust tests with a random
token in the prompt.

## The shim pattern (providers with non-/v1 paths)

The shims live in `tools/ai-gateway-shims/` — one generic Worker, one wrangler
environment per provider (`zai-shim` → z.ai Coding Plan, `opencode-shim` →
OpenCode Zen Go). Each rewrites `POST /v1/chat/completions` → the provider's
real path, forwarding headers and streaming the response back. The gateway
attaches the BYOK key as `Authorization` on its upstream call, so the shims
hold no secrets. Three behaviors beyond the rewrite:

- **Access control**: the `SHIM_TOKEN` wrangler secret gates the Worker — set
  it (`echo "<token>" | npx wrangler secret put SHIM_TOKEN --name <name>`) and
  mirror the value in the custom provider's `headers` field
  (`{"x-shim-token":"<token>"}` as a JSON-encoded string); the gateway
  attaches that header to upstream calls. Without the secret the Worker is an
  open proxy to a paid upstream.
- **Error remap**: z.ai delivers business errors (auth, quota) as HTTP 200
  with a JSON error body; the shim buffers non-SSE JSON 2xx responses and
  remaps error-shaped bodies to 502 so the fallback cascade fires. SSE and
  non-JSON responses stream through untouched.
- **Timeout**: `UPSTREAM_TIMEOUT_MS` aborts a hung upstream and returns 502
  (cascade) — set it at or below the LARGEST model-node timeout among routes
  using the shim; a shorter node's own timeout fires first and its fallback
  proceeds while the shim finishes alone.

- Costs nothing at harness scale: Workers free tier = 100k requests/day; a
  passthrough is I/O-only so the 10ms CPU cap does not bind. On Workers Paid,
  10M requests/mo are included.
- Deploy: `tools/ai-gateway-shims/deploy.sh` (needs `npx wrangler login`
  once), or dashboard paste (Workers & Pages → Create). New provider = new
  `[env.<name>]` block in `wrangler.toml` + a line in `deploy.sh`, then point
  the custom provider's base_url at `https://<name>.<account-subdomain>.workers.dev`.

## Model ids and catalog drift (OpenCode Zen Go worked example)

- Custom-provider catalogs may use **bare model ids** (`deepseek-v4-flash`,
  `mimo-v2.5`) — vendor-prefixed ids (`deepseek/deepseek-v4-flash`) are
  rejected with `Model ... is not supported`. Check the catalog:
  `GET {base}/v1/models` is public for OpenCode Zen Go.
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
