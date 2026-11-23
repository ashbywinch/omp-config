#!/usr/bin/env bash
# Stay in the loop for one PR: tell the worker what needs doing, and tell the
# desk when the PR is ready for the person's approval. Exit when it lands.
#
#   pr-desk-watch.sh <pr> [owner/name] [interval-seconds]
#
# Start it in the background for the life of the PR. It reports two classes of
# need, one message per state change and nothing while the state holds:
#
#   agent work    a review thread whose last voice is not ours (pr-threads),
#                 and a failing REQUIRED check on the current head. That
#                 signature is the head plus the failing names, so a fixed
#                 re-run clears it and a fresh breakage notifies again.
#   human action  the PR is ready for approval: pr-ready says READY — the head
#                 merges into origin/main, every required check is green, no
#                 thread is unanswered — and GitHub's reviewDecision is not
#                 APPROVED. The message carries the PR link and the words
#                 "ready for your approval".
#
# Two recipients, and they are not interchangeable:
#
#   PASEO_AGENT_ID        the agent that owns this PR; receives agent work.
#   PR_DESK_HUMAN_AGENT   the top-level desk agent, the one the person talks
#                         to; receives the approval notice.
#
# A subagent is not a channel to a human. A message sent to a worker is read by
# that worker and never reaches the person, so the approval notice is never
# addressed to PASEO_AGENT_ID by default: PR_DESK_HUMAN_AGENT must be set, and
# the watcher refuses to start without it. Readiness is discovered by polling —
# a watcher that could see the moment and had nowhere to send it would drop it
# silently, which is the one failure this tool exists to prevent.
#
# It never approves, never resolves a thread, never pushes, never merges. The
# approval is the person's.
set -uo pipefail

pr="${1:?usage: pr-desk-watch.sh <pr> [owner/name] [interval-seconds]}"
repo="${2:-}"
interval="${3:-60}"
agent="${PASEO_AGENT_ID:-}"
human="${PR_DESK_HUMAN_AGENT:-}"
root="${PR_READY_ROOT:-$PWD}"

if ! printf '%s' "$pr" | grep -Eq '^[0-9]+$'; then
  echo "pr-desk-watch: <pr> must be a pull request number, got '$pr'" >&2
  exit 2
fi
if ! printf '%s' "$interval" | grep -Eq '^[1-9][0-9]*$'; then
  echo "pr-desk-watch: interval-seconds must be a positive whole number, got '$interval'" >&2
  exit 2
fi

if [ -z "$agent" ]; then
  echo "pr-desk-watch: PASEO_AGENT_ID is not set — no agent would receive the work notices" >&2
  exit 2
fi
if [ -z "$human" ]; then
  echo "pr-desk-watch: PR_DESK_HUMAN_AGENT is not set — a 'ready for approval' notice would have no channel to the person" >&2
  exit 2
fi

repo="${repo:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)}"
if [ -z "$repo" ]; then
  echo "pr-desk-watch: not in a checkout, and no owner/name given" >&2
  exit 2
fi

# A tool that cannot read the PR's state reports "nothing to do" forever, which
# looks the same as a quiet PR. Every source of state is required to be here.
for tool in gh jq pr-threads pr-ready; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "pr-desk-watch: $tool is not on PATH — run 'make install' in omp-config" >&2
    exit 2
  fi
done

slug="$pr ($repo)"
notified_threads=""
notified_checks=""
notified_ready=""
required=""
required_for=""

notify() {  # notify <agent-id> <message>
  paseo send "$1" "$2" >/dev/null 2>&1 || echo "pr-desk-watch: send to $1 failed" >&2
}

# The contexts this base branch requires, from both places GitHub records them:
# classic branch protection and rulesets. Empty means the API would not say,
# and the caller then treats every check as required — the conservative way.
required_contexts() {  # <owner/name> <base>
  local owner="${1%%/*}" name="${1#*/}"
  {
    gh api graphql \
      -f query='query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}' \
      -f o="$owner" -f n="$name" -f b="refs/heads/$2" \
      --jq '.data.repository.ref.branchProtectionRule.requiredStatusCheckContexts[]?' 2>/dev/null
    gh api "repos/$1/rules/branches/$2" \
      --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context' 2>/dev/null
  } | sort -u
}

# The failing required checks on a head, as one comma-joined line. One run per
# name (the latest), because a re-run supersedes the run before it. Paged to
# the end of the list: a commit with more than 100 runs is unusual, and a
# failure hiding on page two would be reported as green.
failing_required() {  # <owner/name> <head> <newline-separated contexts>
  gh api --paginate "repos/$1/commits/$2/check-runs?per_page=100&filter=latest" \
    --jq '.check_runs[]' 2>/dev/null | jq -s -r --arg req "$3" '
    ($req | split("\n") | map(select(. != ""))) as $required
    | group_by(.name)
    | map(sort_by(.started_at) | last)
    | map(select(($required | length) == 0
          or (.name as $n | any($required[]; . == $n))))
    | map(select(.status == "completed"
          and (.conclusion | IN("failure", "timed_out", "action_required", "startup_failure"))))
    | map(.name) | unique | join(", ")
  ' 2>/dev/null
}

while :; do
  view=$(gh pr view "$pr" --repo "$repo" \
    --json state,headRefOid,reviewDecision,baseRefName,url \
    --jq '[.state, .headRefOid, (.reviewDecision // ""), .baseRefName, .url] | @tsv' 2>/dev/null)
  if [ -z "$view" ]; then
    sleep "$interval"
    continue
  fi
  IFS=$'\t' read -r state head decision base url <<< "$view"

  if [ "$state" = "MERGED" ] || [ "$state" = "CLOSED" ]; then
    echo "PR $slug is $state — watcher done"
    exit 0
  fi

  if [ "$base" != "$required_for" ]; then
    required=$(required_contexts "$repo" "$base")
    required_for="$base"
  fi

  threads=$(pr-threads "$pr" --repo "$repo" 2>/dev/null)
  pending=$(printf '%s\n' "$threads" | grep "UNANSWERED" || true)
  if [ -n "$pending" ]; then
    signature=$(printf '%s\n' "$pending" | sort)
    if [ "$signature" != "$notified_threads" ]; then
      count=$(printf '%s\n' "$pending" | wc -l | tr -d ' ')
      notify "$agent" "PR $slug: $count unanswered review thread(s) on ${head:0:7}. Run: pr-threads $pr --repo $repo — answer each with evidence, fix what is real, push once."
      notified_threads="$signature"
    fi
  else
    notified_threads=""
  fi

  broken=$(failing_required "$repo" "$head" "$required")
  if [ -n "$broken" ]; then
    signature="$head $broken"
    if [ "$signature" != "$notified_checks" ]; then
      notify "$agent" "PR $slug: failing required check(s) on ${head:0:7}: $broken. Read the failing step, fix the cause, push once."
      notified_checks="$signature"
    fi
  else
    notified_checks=""
  fi

  # Readiness is asked only of a PR whose cheap signals are already clean —
  # pr-ready is the authority, and it runs the same checks again plus the merge.
  if [ -z "$pending" ] && [ -z "$broken" ] && [ "$decision" != "APPROVED" ]; then
    ready_out=$(pr-ready "$pr" --repo "$repo" --root "$root" --no-wait 2>/dev/null)
    rc=$?
    if [ "$rc" -eq 0 ] && printf '%s\n' "$ready_out" | grep -q '^READY'; then
      signature="$head"
      if [ "$signature" != "$notified_ready" ]; then
        notify "$human" "PR $slug is ready for your approval — $url (head ${head:0:7}: merges cleanly into origin/$base, required checks green, no unanswered threads). The approval is yours; this watcher will not approve, resolve or merge."
        notified_ready="$signature"
      fi
    else
      notified_ready=""
    fi
  else
    notified_ready=""
  fi

  sleep "$interval"
done
