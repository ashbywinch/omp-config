#!/usr/bin/env bash
# Always-armed review notifier: block until a thread is unanswered, then exit.
#
#   pr-watch.sh <pr> [owner/name] [interval-seconds]
#
# `pr-threads --wait` returns as soon as the reviewer has finished on the
# current head, so one call answers "what is unanswered now" and then stops
# watching. Comments arrive afterwards, from the bot on a later pass or from a
# person at any time.
#
# This wrapper re-arms after every answer: it polls, and exits only when an
# unanswered thread exists, printing it.
#
# Launch it in the background.
#
# Its exit is the wake-up.
#
# Every watcher here fails loudly at startup rather than poll a question it
# cannot answer: an unreadable repo or a missing helper would otherwise look
# exactly like a quiet PR, forever.
#
# The desk's long-lived companion — which stays with one PR and also reports a
# failing required check and a ready-for-approval state — is pr-desk-watch.sh.
#
# It never resolves a thread and never pushes. Answering is the agent's job.
set -uo pipefail

pr="${1:?usage: pr-watch.sh <pr> [owner/name] [interval-seconds]}"
repo="${2:-}"
interval="${3:-30}"

if ! printf '%s' "$pr" | grep -Eq '^[0-9]+$'; then
  echo "pr-watch: <pr> must be a pull request number, got '$pr'" >&2
  exit 2
fi
if ! printf '%s' "$interval" | grep -Eq '^[1-9][0-9]*$'; then
  echo "pr-watch: interval-seconds must be a positive whole number, got '$interval'" >&2
  exit 2
fi
if ! command -v pr-threads >/dev/null 2>&1; then
  echo "pr-watch: pr-threads is not on PATH — run 'make install' in omp-config" >&2
  exit 2
fi

repo="${repo:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)}"
if [ -z "$repo" ]; then
  echo "pr-watch: not in a checkout, and no owner/name given" >&2
  exit 2
fi

while :; do
  out=$(pr-threads "$pr" --repo "$repo" --wait 2>/dev/null)
  if printf '%s\n' "$out" | grep -q "UNANSWERED"; then
    printf '%s\n' "$out"
    exit 0
  fi
  sleep "$interval"
done
