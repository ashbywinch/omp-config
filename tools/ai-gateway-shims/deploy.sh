#!/usr/bin/env bash
# Deploy the AI Gateway provider shims (requires `npx wrangler login` once).
#   zai-shim:      route nodes -> z.ai GLM Coding Plan endpoint
#   opencode-shim: route nodes -> OpenCode Zen Go endpoint
#
# After (re)deploying a NEW worker name, also set its SHIM_TOKEN secret:
#   echo "<token>" | npx wrangler secret put SHIM_TOKEN
# and mirror the token in the custom provider's `headers` field.
set -euo pipefail
cd "$(dirname "$0")"
npx --yes wrangler deploy
npx --yes wrangler deploy -e opencode
