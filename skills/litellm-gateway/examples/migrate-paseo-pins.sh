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
# The match is literal at both ends: `grep -F` finds the pin, and the rewrite
# substitutes the exact string. A model id is data, not a pattern — ids like
# `openai/gpt-4o` contain regex metacharacters, so a regex rewrite would carry
# an escape set that is one edit away from being wrong.

if ! files=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'nothing to do: no file under %s carries the old pin\n' "$AGENTS"
  exit 0
fi

printf '%s\n' "$files" | while IFS= read -r f; do
  python3 - "$f" "$OLD_MODEL" "$NEW_MODEL" <<'PY'
import pathlib, sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
file = pathlib.Path(path)
file.write_text(file.read_text().replace(f'"model": "{old}"', f'"model": "{new}"'))
PY
  printf 'rewritten %s\n' "$f"
done

if remaining=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'FAIL: %s file(s) still carry the old pin\n' "$(printf '%s\n' "$remaining" | wc -l)"
  exit 1
fi
printf 'OK: every pin now reads %s\n' "$NEW_MODEL"
