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

OLD_MODEL=${OLD_MODEL:-cloudflare-gateway/dynamic/fallback2}
NEW_MODEL=${NEW_MODEL:-litellm/primary}
AGENTS=${AGENTS_DIR:-$HOME/.paseo/agents}
# `grep -F` matches the model id literally; the sed pattern is a regex, so its
# metacharacters are escaped — a model id like deepseek-v4.1-flash must not
# match anything but itself.
OLD_ESC=$(printf '%s' "$OLD_MODEL" | sed 's/[][\.*^$]/\\&/g')
NEW_ESC=$(printf '%s' "$NEW_MODEL" | sed 's/[&\\]/\\&/g')

if ! files=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'nothing to do: no file under %s carries the old pin\n' "$AGENTS"
  exit 0
fi

printf '%s\n' "$files" | while IFS= read -r f; do
  sed -i "s|\"model\": \"$OLD_ESC\"|\"model\": \"$NEW_ESC\"|g" "$f"
  printf 'rewritten %s\n' "$f"
done

if remaining=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'FAIL: %s file(s) still carry the old pin\n' "$(printf '%s\n' "$remaining" | wc -l)"
  exit 1
fi
printf 'OK: every pin now reads %s\n' "$NEW_MODEL"
