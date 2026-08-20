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

## Never do

- Delete/overwrite `cf-proxy.ts` without creating a systemd service replacement
- Expose `CLOUDFLARE_AIGATEWAY_TOKEN` in logs, code, or docs
- Expect `PATCH` on a route to update its elements — it only renames the route. Creating a new version (`POST .../versions`) and deploying it (`POST .../deployments`) is the correct way to update timeouts and model nodes.
- Assume the model node `timeout` is first-byte or last-byte — set it generously (~1800s) to cover both cases.
- Set `tier.openai = none` (disables the OpenAI provider entirely)
- Skip the `pr-agent-config` branch pin — any PR branch could ship its own `api_base`
- Forget `make install` + restart omp after editing this skill — changes are not live until installed