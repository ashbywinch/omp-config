#!/usr/bin/env bash
# Rewrite the Paseo per-session model pins to `litellm/primary`.
#
# Run with the Paseo daemon STOPPED — in-memory session state flushes back on
# shutdown and reverts an edit made under a live daemon:
#
#   systemctl --user stop paseo
#   bash ~/.omp/agent/skills/litellm-gateway/examples/migrate-paseo-pins.sh
#   systemctl --user start paseo
#
# The match is exact, so historical `lastError` strings — which name the old
# model as `model=...` — are spared.
set -euo pipefail

OLD=cloudflare-gateway/dynamic/fallback2
NEW=litellm/primary
AGENTS=${AGENTS_DIR:-$HOME/.paseo/agents}

if ! files=$(grep -rl "\"model\": \"$OLD\"" "$AGENTS" --include='*.json'); then
  printf 'nothing to do: no file under %s carries the old pin\n' "$AGENTS"
  exit 0
fi

printf '%s\n' "$files" | while IFS= read -r f; do
  sed -i "s|\"model\": \"$OLD\"|\"model\": \"$NEW\"|g" "$f"
  printf 'rewritten %s\n' "$f"
done

if remaining=$(grep -rl "\"model\": \"$OLD\"" "$AGENTS" --include='*.json'); then
  printf 'FAIL: %s file(s) still carry the old pin\n' "$(printf '%s\n' "$remaining" | wc -l)"
  exit 1
fi
printf 'OK: every pin now reads %s\n' "$NEW"
