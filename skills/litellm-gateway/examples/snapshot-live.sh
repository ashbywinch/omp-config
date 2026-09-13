#!/usr/bin/env bash
# Snapshot the live LiteLLM chain before any live-side command.
#
# Usage:
#   snapshot-live.sh                # BASE defaults to ~/.paseo/litellm
#   BASE=/path/to/dir snapshot-live.sh
#
# Prints the backup path plus the exact restore lines to state. Changes
# nothing live: one readlink, one cp.
set -euo pipefail

BASE="${BASE:-$HOME/.paseo/litellm}"
CURRENT="$BASE/config.current.yaml"

LIVE_LINK="$(readlink "$CURRENT" 2>/dev/null || true)"
if [ -z "${LIVE_LINK:-}" ]; then
  echo "FAIL: $CURRENT symlink is broken" >&2
  exit 1
fi
case "$LIVE_LINK" in
  /*) LIVE_FILE="$LIVE_LINK" ;;
  *) LIVE_FILE="$BASE/$LIVE_LINK" ;;
esac
if [ ! -f "$LIVE_FILE" ]; then
  echo "FAIL: live file missing: $LIVE_FILE" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$BASE/config.live-backup-$STAMP.yaml"
cp "$LIVE_FILE" "$BACKUP"

HEAD="$(sed -n 's/.*fallbacks: *\[{"\([^"]*\)".*/\1/p' "$LIVE_FILE" | head -n 1)"
echo "backup: $BACKUP"
echo "live: $LIVE_FILE (head=${HEAD:-unknown})"
echo "restore:"
echo "  cp $BACKUP $LIVE_FILE && systemctl --user restart litellm"
