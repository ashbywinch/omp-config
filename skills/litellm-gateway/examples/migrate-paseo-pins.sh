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

if [ ! -d "$AGENTS" ]; then
  printf 'error: agents directory not found: %s\n' "$AGENTS" >&2
  exit 1
fi

if ! files=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'nothing to do: no file under %s carries the old pin\n' "$AGENTS"
  exit 0
fi

printf '%s\n' "$files" | while IFS= read -r f; do
  python3 - "$f" "$OLD_MODEL" "$NEW_MODEL" <<'PY'
import json, pathlib, sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
file = pathlib.Path(path)
text = file.read_text()

# The JSON parse proves the file is intact and the top-level pin is the field
# being rewritten; the literal substitute then leaves every other byte alone.
def skip(reason):
    print(f"skip {path}: {reason}", file=sys.stderr)
    raise SystemExit(0)

try:
    data = json.loads(text)
except json.JSONDecodeError as err:
    skip(f"invalid JSON ({err})")
if data.get("model") != old:
    skip(f"top-level model is not {old}")

needle = f'"model": "{old}"'
if text.count(needle) != 1:
    skip(f"{text.count(needle)} literal matches, expected 1")

file.write_text(text.replace(needle, f'"model": "{new}"'))
print(f"rewritten {path}")
PY
done

if remaining=$(grep -Frl "\"model\": \"$OLD_MODEL\"" "$AGENTS" --include='*.json'); then
  printf 'FAIL: %s file(s) still carry the old pin\n' "$(printf '%s\n' "$remaining" | wc -l)"
  exit 1
fi
printf 'OK: every pin now reads %s\n' "$NEW_MODEL"
