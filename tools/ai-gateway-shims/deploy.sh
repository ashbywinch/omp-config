#!/usr/bin/env bash
# Deploy the AI Gateway provider shims (requires `npx wrangler login` once).
#   zai-shim:      route nodes -> z.ai GLM Coding Plan endpoint
#   opencode-shim: route nodes -> OpenCode Zen Go endpoint
#
# After (re)deploying a NEW worker name, set its SHIM_TOKEN secret — the auth
# guard fails closed without it:
#   echo "<token>" | npx --yes wrangler secret put SHIM_TOKEN              # zai-shim
#   echo "<token>" | npx --yes wrangler secret put SHIM_TOKEN --env opencode
# and mirror the token in the custom provider's `headers` field.
set -euo pipefail
cd "$(dirname "$0")"
npx --yes wrangler deploy
npx --yes wrangler deploy -e opencode
