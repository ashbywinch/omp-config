#!/bin/bash
# wait-for.sh — block until a pid exits, then print the tail of its log.
# Run it as the harness's background command so the completion event is the
# real process's exit, not the shell that launched it.
#
# Usage: wait-for <pid> [log]
set -euo pipefail

pid="${1:?usage: wait-for <pid> [log]}"
log="${2:-}"

tail --pid="$pid" -f /dev/null

if [ -n "$log" ] && [ -f "$log" ]; then
  echo "=== $log (tail) ==="
  tail -n 25 "$log"
else
  echo "pid $pid exited"
fi
