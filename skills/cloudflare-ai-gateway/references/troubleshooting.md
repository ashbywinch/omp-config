# Troubleshooting

## 504 Gateway Timeout

**Observed**: PR-Agent review runs returned 504 at ~94s.

**Root cause**: The model node timeout was too short. DeepSeek needed more time than the route's timeout allowed. Query current route timeouts via the routes API.

**Workers 100s limit disproven**: The review ran for 10 minutes through the gateway without issue. The AI Gateway does not inherit the Workers 100s execution limit.

## 502 / "Failed to get response from provider"

- Check proxy running: `systemctl --user is-active cf-gateway-proxy.service`
- Test gateway directly: `curl -s "$OPENAI_BASE_URL/v1/chat/completions" -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_TOKEN" -H "Content-Type: application/json" -d '{"model":"dynamic/fallback2","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check DeepSeek has credits: `curl -s "https://api.deepseek.com/v1/chat/completions" -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check the provider API key is set in the environment

## "Model not found" / Falls back to Opus 4.8

OMP's model registry doesn't have the Cloudflare dynamic route names. Fix:
1. `models.yml` must define the `cloudflare-gateway` provider with the model IDs
2. `tier.openai` must be `auto` (not `none`)
3. `modelRoles` in `config.yml` must use `cloudflare-gateway/dynamic/...`

## Proxy not starting at boot

- `systemctl --user is-enabled cf-gateway-proxy.service` — must be `enabled`
- `loginctl show-user ashby | grep Linger` — must be `yes` for user services at boot

## "Incorrect API key provided: sk-..."

Check `PR_AGENT_CONFIG_BRANCH` pin first, not the key. Without the pin, the image defaults run (model `gpt-5.6`, `api_base api.openai.com`) and reject the key.

## 403 Access denied (HTML page, "used Cloudflare to restrict access")

**Observed**: a urllib client calling the proxy got an HTML 403 block; the
same request via `curl` succeeded.

**Root cause**: the Cloudflare WAF rejects the default `urllib`/custom
User-Agent. The known-good value is `opencode/1.14.20` — the same UA the
OMP client sends. Any custom client must set a browser/known UA; a UA like
`the-loft/0.1` or the urllib default gets blocked.

**Fix**: set `User-Agent: opencode/1.14.20` on every chat-completions
request (see `tools/ai_client.py` in the-loft — the comment records this).

## Empty content / `finish_reason: "length"` with zero output

**Observed**: a reasoning model (e.g. `xiaomi/mimo-v2.5`) returned
`content: null` and `finish_reason: "length"` — it burned the whole token
budget on `reasoning` tokens and never produced output. Small `max_tokens`
(e.g. 4096) or no `max_tokens` at all reproduced it; `max_tokens: 32000`
fixed it (a 25-line orientation report consumed ~3900 reasoning + ~960
completion tokens).

**Fix**: give reasoning models large `max_tokens` headroom (≥32000 for
vision/geometry tasks). The client should also distinguish "reasoning ate
the budget" (raise max_tokens) from "model refused" (fix the prompt) in
its error message.

## "This model has been deprecated. It is recommended to migrate to ..."

**Observed**: `dynamic/image` returned HTTP 404 with this body — the route
pointed at a deprecated model (`opencode-go/mimo-v2-flash`).

**Fix**: update the route's model nodes to the recommended model. The
correct procedure (the "Never do" entry below): `POST
/routes/{id}/versions` with the full `elements` array (START → model nodes
→ END), then `POST /routes/{id}/deployments` with `{"version_id": ...}`.
The version list at `GET /routes/{id}/versions` shows which version is
`active`. Keep the original providers — only change the model names; a
provider swap (e.g. `custom-opencode-go` → `openrouter`) changes the
request path and can break auth.

## Updating a route's model nodes — the exact procedure

1. `GET /routes` → find the route id by name.
2. `GET /routes/{id}/versions` → read the current `data` (the `elements`
   array) — copy it as the base.
3. Edit the model names in the `properties` of the `model` nodes. Keep the
   providers and the START/END structure; both model nodes need both
   `success` and `fallback` outputs pointing at the END.
4. `POST /routes/{id}/versions` with `{"account_id": ..., "elements":
   [...]}` → returns the new version id.
5. `POST /routes/{id}/deployments` with `{"version_id": ...}` → makes it
   active.
6. Verify: `GET /routes/{id}/versions` shows the new version `active: true`
   (not just listed), then a test chat-completions call.

The route's `version.active` only flips after the deployment step — a
created-but-undeployed version leaves the OLD (possibly empty/broken)
version active.

## Never do

- Delete/overwrite `cf-proxy.ts` without creating a systemd service replacement
- Expose `CLOUDFLARE_AIGATEWAY_TOKEN` in logs, code, or docs
- Expect `PATCH` on a route to update its elements — it only renames the route. Creating a new version (`POST .../versions`) and deploying it (`POST .../deployments`) is the correct way to update timeouts and model nodes.
- Assume the model node `timeout` is first-byte or last-byte — set it generously (~1800s) to cover both cases.
- Set `tier.openai = none` (disables the OpenAI provider entirely)
- Skip the `pr-agent-config` branch pin — any PR branch could ship its own `api_base`
- Forget `make install` + restart omp after editing this skill — changes are not live until installed
- Swap providers when updating a model name — keep the original provider
  (`custom-opencode-go`, `openrouter`, ...); a provider change alters the
  request path and can break auth or the working fallback.
- Leave a created route version undeployed — the old (possibly empty or
  broken) version stays active; always deploy and verify.