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
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"
```

Each log entry includes:

| Field | Description |
|---|---|
| `created_at` | Timestamp |
| `model` | Model name (e.g. `deepseek-v4-flash`) |
| `provider` | Provider slug (e.g. `custom-opencode-go`, `deepseek`) |
| `cost` | Cost in USD |
| `duration` | Duration in milliseconds |
| `tokens_in` | Input tokens |
| `tokens_out` | Output tokens |
| `status_code` | HTTP status code |
| `metadata` | Custom metadata JSON (source, repo) |
| `step` | Route step that handled the request |

## Cost breakdown by source

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs?limit=100" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN" \
  | python3 -c "
import json, sys
logs = json.load(sys.stdin).get('result', [])
by_source = {}
for log in logs:
    meta = log.get('metadata') or {}
    source = meta.get('source', 'unknown') if isinstance(meta, dict) else 'unknown'
    repo = meta.get('repo', 'unknown') if isinstance(meta, dict) else 'unknown'
    cost = log.get('cost', 0) or 0
    key = f'{source}/{repo}'
    by_source.setdefault(key, {'count': 0, 'cost': 0.0, 'duration': 0})
    by_source[key]['count'] += 1
    by_source[key]['cost'] += cost
    by_source[key]['duration'] += log.get('duration', 0) or 0

for key in sorted(by_source):
    s = by_source[key]
    cost_str = f\"\${s['cost']:.4f}\"
    print(f'{key:30s} {s[\"count\"]:3d} req  {cost_str}  {s[\"duration\"]/1000:.0f}s total')
"
```

## Cost breakdown by model

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs?limit=100" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN" \
  | python3 -c "
import json, sys
logs = json.load(sys.stdin).get('result', [])
by_model = {}
for log in logs:
    model = log.get('model', 'unknown')
    cost = log.get('cost', 0) or 0
    by_model.setdefault(model, {'count': 0, 'cost': 0.0})
    by_model[model]['count'] += 1
    by_model[model]['cost'] += cost
for m in sorted(by_model):
    s = by_model[m]
    print(f'{m:40s} {s[\"count\"]:3d} req  ${s[\"cost\"]:.4f}')
"
```

## View a specific log request/response

```bash
LOG_ID=<log-id>
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs/$LOG_ID/request" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"

curl -s "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai-gateway/gateways/$GATEWAY/logs/$LOG_ID/response" \
  -H "Authorization: Bearer $CLOUDFLARE_AIGATEWAY_ADMIN_TOKEN"
```

## Known cost observations

| Source | Typical cost | Typical duration |
|---|---|---|
| Local agent session (short request) | ~$0.0002 | ~14s |
| PR-Agent review (32K-token diff) | ~$0.007 | ~290s |
| PR-Agent improve (code suggestions) | ~$0.005 | ~205s |

## Notes

- The `cfut_` runtime token cannot query logs — use the admin token.
- Metadata is only logged when the `cf-aig-metadata` header is sent (proxy for local, `[litellm] extra_headers` for PR-Agent).
- Logs have a retention period (check Cloudflare dashboard for your plan).