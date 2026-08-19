---
name: cloudflare-ai-gateway-analytics
description: Query Cloudflare AI Gateway logs and analytics via API — cost per request, per-repo breakdown, duration, model usage
---

# Cloudflare AI Gateway Analytics

Query per-request logs from Cloudflare AI Gateway. Each log entry includes cost, duration, tokens, model, provider, and custom metadata (source, repo) injected by the local proxy or PR-Agent config.

## Prerequisites

- `CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN` — API token with AI Gateway Edit permission
- `ACCOUNT_ID` and `GATEWAY` env vars (or replace inline). Find them in the Cloudflare dashboard URL: `https://dash.cloudflare.com/{ACCOUNT_ID}/ai/ai-gateway/gateways/{GATEWAY}`

```bash
export ACCOUNT_ID=<your-account-id>
export GATEWAY=default
```

## List recent logs

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs?limit=20" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN" | jq '.result[] | {created_at, model, cost, duration, metadata}'
```

## Cost breakdown by source/repo

Fetch logs and aggregate by `metadata.source` and `metadata.repo`:

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs?limit=100" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"
```

The response includes `cost` (USD), `duration` (ms), `model`, `provider`, and `metadata` (JSON with `source` and `repo` when tagged). Aggregate by metadata fields to see per-source/repo costs.

## Cost breakdown by model

Same endpoint, group by `model` field.

## View a specific log request/response

```bash
LOG_ID=<log-id>
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs/$LOG_ID/request" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"

curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs/$LOG_ID/response" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"
```

## Notes

- The `cfut_` runtime token cannot query logs — use the admin token.
- Metadata is only logged when the `cf-aig-metadata` header is sent (proxy for local, `[litellm] extra_headers` for PR-Agent).
- Logs have a retention period (check Cloudflare dashboard for your plan).