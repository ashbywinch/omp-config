#!/usr/bin/env bash
# Watch one PR: tell the worker what needs doing, and tell the desk when the PR
# is ready for the person's approval.
#
#   pr-desk-watch.sh <pr> [owner/name] [interval-seconds]
#
# Start it in the background for the life of the PR.
#
# The watcher exits when the PR merges or closes. It reports two classes of
# need, one message per state change and nothing while the state holds:
#
#   agent work    a review thread whose last voice is not ours (pr-threads),
#                 and a failing REQUIRED check on the current head. The thread
#                 signature is the unanswered threads' ids, so a push that only
#                 moves their lines notifies nothing; the check signature is the
#                 head plus the failing names, so a fixed re-run clears it and a
#                 fresh breakage notifies again.
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
# A notice that could not be sent is not recorded as sent: the signature stays
# unset and the next pass sends it again.
#
# A read that does not answer is not an answer. Every GitHub call is bounded by
# PR_DESK_WATCH_TIMEOUT seconds (30 by default), and a pass that cannot read the
# PR says so on stderr rather than looking quiet.
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
# The slug is interpolated into API paths, so it is held to the shape GitHub
# uses. Every use is quoted already; this refuses the value rather than relying
# on that everywhere.
if ! printf '%s' "$repo" | grep -Eq '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$'; then
  echo "pr-desk-watch: repo must be owner/name, got '$repo'" >&2
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

# The sink is required for the same reason: without it every notice fails, and
# a watcher that cannot deliver is a watcher that never wakes anybody.
if ! command -v paseo >/dev/null 2>&1; then
  echo "pr-desk-watch: paseo is not on PATH — no notice could be delivered" >&2
  exit 2
fi

# A call that hangs is a watcher that stops watching, so every read is bounded.
if ! command -v timeout >/dev/null 2>&1; then
  echo "pr-desk-watch: timeout (coreutils) is not on PATH — a hung read would freeze the watcher" >&2
  exit 2
fi
read_timeout="${PR_DESK_WATCH_TIMEOUT:-30}"
if ! printf '%s' "$read_timeout" | grep -Eq '^[1-9][0-9]*$'; then
  echo "pr-desk-watch: PR_DESK_WATCH_TIMEOUT must be a positive whole number of seconds, got '$read_timeout'" >&2
  exit 2
fi

slug="$pr ($repo)"
notified_threads=""
notified_checks=""
notified_ready=""
required=""
required_for=""

# Every read of GitHub's state goes through here: one place bounds the wait, and
# a non-zero exit is the caller's to handle as "unknown", never as "clean".
gh_read() {  # gh_read <gh args...>
  timeout "$read_timeout" gh "$@"
}

# A failed send returns non-zero so the caller leaves its signature unset: the
# notice is re-sent next pass instead of being recorded as delivered. Both of
# the sender's streams are captured, so "agent not found" survives whichever one
# it is written to; on success the text is simply not used.
notify() {  # notify <agent-id> <message>
  local said
  # `pipefail` is set, so the pipeline still reports the sender's failure.
  said=$(paseo send "$1" "$2" 2>&1 | tr '\n' ' ') && return 0
  echo "pr-desk-watch: send to $1 failed — ${said:-no message} — retrying next pass" >&2
  return 1
}

# The contexts this base branch requires, from both places GitHub records them:
# classic branch protection and rulesets. Empty means the API would not say,
# and the caller then treats every check as required — the conservative way.
# A source that fails is the same as a source that will not say: a partial list
# would silently drop a required check, so either failure returns empty.
required_contexts() {  # <owner/name> <base>
  local owner="${1%%/*}" name="${1#*/}" classic rules
  classic=$(gh_read api graphql \
    -f query='query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}' \
    -f o="$owner" -f n="$name" -f b="refs/heads/$2" \
    --jq '.data.repository.ref.branchProtectionRule.requiredStatusCheckContexts[]?' 2>/dev/null) || {
    echo "pr-desk-watch: branch protection unreadable — treating every check as required" >&2
    return 0
  }
  rules=$(gh_read api "repos/$1/rules/branches/$2" \
    --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context' 2>/dev/null) || {
    echo "pr-desk-watch: rulesets unreadable — treating every check as required" >&2
    return 0
  }
  printf '%s\n%s\n' "$classic" "$rules" | sed '/^$/d' | sort -u
}

# The required checks on a head, as one JSON object:
#
#   {"blocked": [...], "failed": [...]}
#
#   blocked   every required check that is not a completed success — running,
#             queued and cancelled included — plus every required context that
#             has no run on the head at all. Readiness needs it empty.
#   failed    the blocked ones with a failure conclusion. This is the list
#             worth a message, because it names something to fix.
#
# A required context with no run is the case GitHub shows as "expected": no
# workflow reported it, so nothing has verified it, and the head cannot be
# called green. It sits in `blocked` rather than `failed` because there is no
# failing step to read.
#
# The state is an object of arrays, not a delimited line, so no check name can
# be mistaken for a separator. The caller gates on `blocked | length`, never on
# a string being empty.
#
# A check is green only when it finished and finished successfully, so the
# absence of `failed` is not greenness: a run still in flight is in `blocked`.
# The cheap gate is therefore never more permissive than `pr-ready`, which
# repeats the check as the authority.
#
# An unreadable list is not a clean one, so the function exits non-zero when
# the answer cannot be trusted: the head is not a commit sha, the call failed,
# the head has no runs at all (absence is not success — `tools/pr_ready.py:11-14`),
# or two runs carry one name, which means `filter=latest` did not reduce them.
#
# One run per name comes from the API (`filter=latest`), not from sorting here:
# `started_at` is null on a run that never started, and a sort on it would
# choose the wrong run for exactly the check that has not begun.
check_state() {  # <owner/name> <head> <newline-separated contexts>
  local runs
  if ! printf '%s' "$2" | grep -Eq '^[0-9a-f]{7,40}$'; then
    echo "pr-desk-watch: '$2' is not a commit sha — check state unknown" >&2
    return 1
  fi
  runs=$(gh_read api --paginate "repos/$1/commits/$2/check-runs?per_page=100&filter=latest" \
           --jq '.check_runs[]' 2>/dev/null) || {
    echo "pr-desk-watch: check-runs unreadable on ${2:0:7} — holding readiness" >&2
    return 1
  }
  printf '%s\n' "$runs" | jq -s -r --arg req "$3" '
    ($req | split("\n") | map(select(. != ""))) as $required
    | map(select(($required | length) == 0
          or (.name as $n | any($required[]; . == $n)))) as $runs
    | if ($runs | length) == 0 then error("no check-runs on this head")
      elif ($runs | map(.name) | length) != ($runs | map(.name) | unique | length)
        then error("two runs for one name — filter=latest was not honoured")
      else $runs end
    | ($required | map(select(. as $r | any($runs[]; .name == $r) | not))) as $missing
    | map(select((.status == "completed" and .conclusion == "success") | not)) as $blocked
    | { blocked: (($blocked | map(.name)) + $missing | unique),
        failed:  ($blocked
                  | map(select(.conclusion
                        | IN("failure", "timed_out", "action_required", "startup_failure")))
                  | map(.name) | unique) }
  ' || {
    echo "pr-desk-watch: the check state above is not usable on ${2:0:7} — holding readiness" >&2
    return 1
  }
}

while :; do
  # The empty reviewDecision is written as "-" so that `read` cannot collapse
  # it: IFS whitespace drops an empty field, and the next two fields — the base
  # and the link — would slide left into the wrong names.
  view=$(gh_read pr view "$pr" --repo "$repo" \
    --json state,headRefOid,reviewDecision,baseRefName,url \
    --jq '[.state, .headRefOid, (.reviewDecision // "-"), .baseRefName, .url] | @tsv' 2>/dev/null)
  if [ -z "$view" ]; then
    # Silence here would look exactly like a quiet PR, which is the failure
    # this tool exists to prevent.
    echo "pr-desk-watch: cannot read $slug — still watching" >&2
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

  # The key is the threads' identities, not their printed position: a push
  # moves path:line for a thread nobody answered, and a listing-shaped key
  # reports that unchanged work as new.
  pending=$(pr-threads "$pr" --repo "$repo" --ids 2>/dev/null | sed '/^$/d' | sort)
  if [ -n "$pending" ]; then
    if [ "$pending" != "$notified_threads" ]; then
      count=$(printf '%s\n' "$pending" | wc -l | tr -d ' ')
      notify "$agent" "PR $slug: $count unanswered review thread(s). Run: pr-threads $pr --repo $repo — answer each with evidence, fix what is real, push once." \
        && notified_threads="$pending"
    fi
  else
    notified_threads=""
  fi

  # An unreadable or ambiguous check list is not a clean one: readiness is held
  # and the reason is printed, rather than the absence of a failure read as green.
  if checks=$(check_state "$repo" "$head" "$required"); then
    blocked=$(printf '%s' "$checks" | jq -r '.blocked | length')
    broken=$(printf '%s' "$checks" | jq -r '.failed | join(", ")')
  else
    blocked=1          # unknown is not clean
    broken=""
  fi
  if [ -n "$broken" ]; then
    signature="$head $broken"
    if [ "$signature" != "$notified_checks" ]; then
      notify "$agent" "PR $slug: failing required check(s) on ${head:0:7}: $broken. Read the failing step, fix the cause, push once." \
        && notified_checks="$signature"
    fi
  else
    notified_checks=""
  fi

  # Readiness is asked only of a PR whose cheap signals are already clean —
  # pr-ready is the authority, and it runs the same checks again plus the merge.
  # `blocked` is the number of required checks that are not a completed success,
  # a running one included, and 1 when the list could not be read, so no pass
  # asks pr-ready about a state it cannot vouch for.
  if [ -z "$pending" ] && [ "$blocked" -eq 0 ] && [ "$decision" != "APPROVED" ]; then
    ready_out=$(pr-ready "$pr" --repo "$repo" --root "$root" --no-wait 2>&1)
    rc=$?
    # pr-ready's verdict is its own line, `READY: <next step>` — the prefix and
    # the colon are the format (`tools/pr_ready.py:197-202`), so a longer word
    # that merely starts with READY cannot match.
    if [ "$rc" -eq 0 ] && printf '%s\n' "$ready_out" | grep -q '^READY:'; then
      signature="$head"
      if [ "$signature" != "$notified_ready" ]; then
        notify "$human" "PR $slug is ready for your approval — $url (head ${head:0:7}: merges cleanly into origin/$base, required checks green, no unanswered threads). The approval is yours; this watcher will not approve, resolve or merge." \
          && notified_ready="$signature"
      fi
    else
      # pr-ready answers BLOCKED with its reasons. No verdict at all is the
      # tool failing to answer, and that reason is worth a line of its own.
      if ! printf '%s\n' "$ready_out" | grep -q '^BLOCKED:'; then
        reason=$(printf '%s\n' "$ready_out" | tail -1)
        echo "pr-desk-watch: pr-ready gave no verdict${reason:+ — $reason}" >&2
      fi
      notified_ready=""
    fi
  else
    notified_ready=""
  fi

  sleep "$interval"
done
