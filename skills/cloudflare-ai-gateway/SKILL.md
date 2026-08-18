---
name: cloudflare-ai-gateway
description: Cloudflare AI Gateway configuration for Paseo/OMP — setup, proxy service, PR-Agent integration, troubleshooting
---

# Cloudflare AI Gateway

Routes Paseo/OMP AI API calls through Cloudflare AI Gateway with OpenCode (primary) → DeepSeek (fallback) and per-repo analytics tagging.

## Architecture

```
OMP agent → local proxy (:9123) → Cloudflare AI Gateway → OpenCode (primary, out of credits)
                                                         → DeepSeek-direct (fallback, funded)
```

The proxy injects `cf-aig-metadata: {"source":"agent","repo":"<repo>"}` for Cloudflare analytics.

## Files

| Path | Purpose |
|---|---|
| `/home/ashby/.paseo/cf-proxy.ts` | Metadata-injecting proxy (Bun) |
| `/home/ashby/.config/systemd/user/cf-gateway-proxy.service` | Systemd user service; survives reboots |
| `/home/ashby/.paseo/omp-yolo.sh` | OMP launcher — tags proxy with repo, sets `OPENAI_BASE_URL` |
| `/home/ashby/.paseo/config.json` | Paseo provider config — model `openai/dynamic/fallback2` |

## Cloudflare Dashboard

- **Account**: `e21a5be58ac1e8f7d5619539feb2dc3d`
- **Gateway**: `default`
- **Dynamic route**: `fallback2` — OpenCode → DeepSeek failover
- **Auth**: uses `CLOUDFLARE_AIGATEWAY_TOKEN` env var (`cfut_...`)

## Proxy service

Managed by systemd — auto-starts on boot, restarts on failure:

```bash
systemctl --user status cf-gateway-proxy.service    # check status
systemctl --user restart cf-gateway-proxy.service   # restart after code change
journalctl --user -u cf-gateway-proxy.service -n 50 # view logs
```

Default port: `9123`. Health check: `curl http://localhost:9123/health`.

## How repo tagging works

1. `omp-yolo.sh` extracts repo name: `git rev-parse --show-toplevel`
2. Tags proxy: `POST http://localhost:9123/_tag` with `repo=<name>`
3. Proxy injects `cf-aig-metadata` header on forwarded requests
4. Cloudflare logs show `source: agent`, `repo: <name>` in analytics

## Troubleshooting

### "Failed to get response from provider" / 502

- Check proxy is running: `systemctl --user is-active cf-gateway-proxy.service`
- Check Cloudflare gateway responds: `curl -s "https://gateway.ai.cloudflare.com/v1/e21a5be58ac1e8f7d5619539feb2dc3d/default/compat/v1/chat/completions" -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_TOKEN" -H "Content-Type: application/json" -d '{"model":"dynamic/fallback2","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'`
- Check DeepSeek has credits: direct call with `deepseek-chat` model
- Check `.secrets` sourced in `start.sh`: `source /home/ashby/.secrets`

### Proxy not starting at boot

- Verify service is enabled: `systemctl --user is-enabled cf-gateway-proxy.service`
- Enable: `systemctl --user enable cf-gateway-proxy.service`
- Check user lingering: `loginctl show-user ashby | grep Linger` — must be `yes` for user services at boot

### Rollback to original OpenCode Go routing

```bash
bash /home/ashby/.paseo/rollback.sh
systemctl --user restart paseo
```

Restores: original `config.json`, original `omp-yolo.sh`, stops/disables proxy.

### PR-Agent (review bot) not routing through gateway

PR-Agent runs in GitHub Actions, not through the local proxy. To route through Cloudflare:

```yaml
env:
  OPENAI_KEY: ${{ secrets.CLOUDFLARE_AIGATEWAY_TOKEN }}
  OPENAI_BASE_URL: https://gateway.ai.cloudflare.com/v1/e21a5be58ac1e8f7d5619539feb2dc3d/default/compat
  OPENAI_CUSTOM_HEADERS: |
    cf-aig-metadata: {"source":"review","repo":"<repo-name>"}
```

`OPENAI_CUSTOM_HEADERS` is read by the OpenAI Python SDK used by PR-Agent.

## Never do

- Delete/overwrite `cf-proxy.ts` without creating a systemd service replacement
- Set `OPENAI_BASE_URL` to anything other than the proxy when Paseo is running through Cloudflare
- Expose `CLOUDFLARE_AIGATEWAY_TOKEN` in logs, code, or docs (it's an env var only)