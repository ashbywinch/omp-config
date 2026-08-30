#!/usr/bin/env bash
# Deploy the AI Gateway provider shims (requires `npx wrangler login` once).
#   zai-shim:      route nodes -> z.ai GLM Coding Plan endpoint
#   opencode-shim: route nodes -> OpenCode Zen Go endpoint
set -euo pipefail
cd "$(dirname "$0")"
npx wrangler deploy
npx wrangler deploy -e opencode
