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

if [ ! -d "$AGENTS" ]; then
  printf 'error: agents directory not found: %s\n' "$AGENTS" >&2
  exit 1
fi

python3 - "$AGENTS" "$OLD_MODEL" "$NEW_MODEL" <<'PY'
import json, pathlib, re, sys

agents, old, new = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]

# The pin is the JSON field `model`, so match the key with optional whitespace
# and the value literally: a model id is data, not a pattern. Last-resort
# history strings hold the old id as `model=...`, which this cannot match.
pin = re.compile(r'("model"\s*:\s*)"' + re.escape(old) + '"')

rewritten = 0
for file in sorted(agents.rglob("*.json")):
    text = file.read_text()
    if old not in text:
        continue
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        print(f"skip {file}: invalid JSON ({err})", file=sys.stderr)
        continue
    if data.get("model") != old:
        print(f"skip {file}: top-level model is not {old}", file=sys.stderr)
        continue
    if len(pin.findall(text)) != 1:
        print(f"skip {file}: {len(pin.findall(text))} pins match, expected 1",
              file=sys.stderr)
        continue
    file.write_text(pin.sub(lambda m: m.group(1) + f'"{new}"', text))
    rewritten += 1
    print(f"rewritten {file}")

# Verify by the same pattern that matched, so a spare `model=` mention in
# unrelated text does not read as a failed migration.
remaining = [str(f) for f in sorted(agents.rglob("*.json")) if pin.search(f.read_text())]
if remaining:
    print(f"FAIL: {len(remaining)} file(s) still pin {old}:", file=sys.stderr)
    for path in remaining:
        print(f"  {path}", file=sys.stderr)
    raise SystemExit(1)
print(f"OK: {rewritten} rewritten; every pin reads {new}")
PY
