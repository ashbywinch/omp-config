#!/usr/bin/env bash
# Watch one PR and tell its owner what needs doing next.
#
#   pr-desk-watch.sh <pr> [owner/name] [interval-seconds]
#
# One recipient, PR_DESK_AGENT: the session that owns this PR. Every message is
# addressed to it, because that session is also the person's channel.
#
# The owner is told one of four things, once per state change:
#
#   a comment arrived      unanswered review threads, keyed by their ids
#   a check failed         a required check that finished unsuccessfully, keyed
#                          by the head plus the failing names
#   the branch is behind   the base moved, so the head must be updated, keyed by
#                          the head once behind
#   ready for review       pr-ready says READY and GitHub has not approved it;
#                          the owner relays this to the person with the link
#
# A steady state sends nothing: each message keeps its key until the state
# changes, and a failed send leaves the key unset so the next pass retries.
#
# Every GitHub read is bounded by PR_DESK_WATCH_TIMEOUT (30s by default). A read
# that does not answer is reported on stderr — never read as "clean".
#
# It never approves, never resolves a thread, never pushes, never merges.
set -uo pipefail

pr="${1:?usage: pr-desk-watch.sh <pr> [owner/name] [interval-seconds]}"
repo="${2:-}"
interval="${3:-60}"
owner="${PR_DESK_AGENT:-}"
root="${PR_READY_ROOT:-$PWD}"

warn() { echo "pr-desk-watch: $*" >&2; }

if ! printf '%s' "$pr" | grep -Eq '^[0-9]+$'; then
  warn "<pr> must be a pull request number, got '$pr'"; exit 2
fi
if ! printf '%s' "$interval" | grep -Eq '^[1-9][0-9]*$'; then
  warn "interval-seconds must be a positive whole number, got '$interval'"; exit 2
fi
if [ -z "$owner" ]; then
  warn "PR_DESK_AGENT is not set — name the session that owns this PR"; exit 2
fi

for tool in gh jq pr-threads pr-ready paseo timeout; do
  command -v "$tool" >/dev/null 2>&1 || {
    warn "$tool is not on PATH"; exit 2; }
done

repo="${repo:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)}"
[ -n "$repo" ] || { warn "not in a checkout, and no owner/name given"; exit 2; }
slug="$repo#$pr"

read_timeout="${PR_DESK_WATCH_TIMEOUT:-30}"
if ! printf '%s' "$read_timeout" | grep -Eq '^[1-9][0-9]*$'; then
  warn "PR_DESK_WATCH_TIMEOUT must be a positive whole number of seconds, got '$read_timeout'"
  exit 2
fi

# Every GitHub read goes through here, so the bound is in one place. A non-zero
# exit means "the answer is unknown", and each caller says what it does next.
gh_read() { timeout "$read_timeout" gh "$@"; }

# Send one notice. A failure is printed and returned, so the caller keeps its
# key unset and the next pass tries again.
notify() {
  local said
  if said=$(paseo send "$1" "$2" 2>&1 | tr '\n' ' '); then
    return 0
  fi
  warn "send to $1 failed — ${said:-no message} — retrying next pass"
  return 1
}

# One field of the PR, or "-" when GitHub leaves it empty.
pr_field() {
  printf '%s' "$view" | jq -r --arg k "$1" '.[$k] // "-"'
}

# The required contexts of a base branch, from branch protection and rulesets.
# Returns non-zero when either source will not answer: a partial list would
# silently drop a required check, and the caller then counts every check.
required_contexts() {
  local owner_name="${1%%/*}" name="${1#*/}" classic rules
  classic=$(gh_read api graphql \
    -f query='query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}' \
    -f o="$owner_name" -f n="$name" -f b="refs/heads/$2" \
    --jq '.data.repository.ref.branchProtectionRule.requiredStatusCheckContexts[]?') || return 1
  rules=$(gh_read api "repos/$1/rules/branches/$2" \
    --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context') || return 1
  printf '%s\n%s\n' "$classic" "$rules" | sed '/^$/d' | sort -u
}

# Load the check runs on a head into `runs`, one JSON object per line and one
# per check name. Returns non-zero when the state cannot be trusted: the head is
# not a sha, the read failed, or there are no runs at all.
load_runs() {
  local head="$2"
  if ! printf '%s' "$head" | grep -Eq '^[0-9a-f]{7,40}$'; then
    warn "'$head' is not a commit sha — check state unknown"; return 1
  fi
  # Read the pages raw, so one jq expression can see every page at once.
  local pages
  pages=$(gh_read api --paginate "repos/$1/commits/$head/check-runs?per_page=100&filter=latest") || {
    warn "check-runs unreadable on ${head:0:7} — holding readiness"; return 1; }
  # `filter=latest` is not reliable: the same name can come back twice (a
  # reusable workflow's job, or a re-run beside the run it replaced). Keep the
  # newest run per name, ordered by `started_at`, which a run that never started
  # leaves null.
  runs=$(printf '%s' "$pages" \
    | jq -cs 'map(.check_runs[]) | group_by(.name) | map(sort_by(.started_at // "") | last) | .[]') || {
    warn "check-runs on ${head:0:7} are not readable JSON — holding readiness"; return 1; }
  if [ -z "$runs" ]; then
    warn "no check-runs on ${head:0:7} — holding readiness"; return 1
  fi
}

# Names of the required checks that are not a completed success. A required
# context with no run is included: GitHub shows it as expected, so nothing has
# verified it.
blocked_names() {
  local required="$1" missing
  printf '%s\n' "$runs" | jq -rs --arg req "$required" '
    ($req | split("\n") | map(select(. != ""))) as $wanted
    | map(select(($wanted | length) == 0 or (.name as $n | any($wanted[]; . == $n))))
    | map(select((.status == "completed" and .conclusion == "success") | not))
    | map(.name)'
  missing=$(comm -23 \
    <(printf '%s\n' "$required" | sed '/^$/d' | sort -u) \
    <(printf '%s\n' "$runs" | jq -r '.name' | sort -u))
  [ -n "$missing" ] && printf '%s\n' "$missing"
}

# Names of the blocked checks that failed, which is the list worth a message.
failed_names() {
  printf '%s\n' "$runs" | jq -rs '
    map(select(.conclusion | IN("failure", "timed_out", "action_required", "startup_failure")))
    | .[].name'
}

notified_threads=""
notified_checks=""
notified_behind=""
notified_ready=""
required=""
required_for=""
runs=""
view=""

while :; do
  view=$(gh_read pr view "$pr" --repo "$repo" \
    --json state,headRefOid,reviewDecision,baseRefName,url,mergeStateStatus) || view=""
  if [ -z "$view" ]; then
    warn "cannot read $slug — still watching"
    sleep "$interval"
    continue
  fi

  state=$(pr_field state)
  head=$(pr_field headRefOid)
  decision=$(pr_field reviewDecision)
  base=$(pr_field baseRefName)
  url=$(pr_field url)
  merge_state=$(pr_field mergeStateStatus)

  if [ "$state" = "MERGED" ] || [ "$state" = "CLOSED" ]; then
    echo "PR $slug is $state — watcher done"
    exit 0
  fi

  if [ "$base" != "$required_for" ]; then
    if required=$(required_contexts "$repo" "$base"); then :; else
      warn "required contexts unreadable for origin/$base — every check counts"
      required=""
    fi
    required_for="$base"
  fi

  # A comment arrived: keyed by the unanswered threads' ids, so a push that
  # only moves their lines notifies nothing.
  pending=$(timeout "$read_timeout" pr-threads "$pr" --repo "$repo" --ids 2>/dev/null \
    | sed '/^$/d' | sort)
  if [ -n "$pending" ]; then
    if [ "$pending" != "$notified_threads" ]; then
      count=$(printf '%s\n' "$pending" | wc -l | tr -d ' ')
      notify "$owner" "PR $slug: $count unanswered review thread(s) on ${head:0:7}. Run: pr-threads $pr --repo $repo — answer each with evidence, fix what is real, push once." \
        && notified_threads="$pending"
    fi
  else
    notified_threads=""
  fi

  # A required check failed: keyed by the head plus the failing names, so a
  # fixed re-run clears it and a fresh breakage notifies again.
  blocked=0
  broken=""
  if load_runs "$repo" "$head"; then
    blocked_list=$(blocked_names "$required")
    blocked=$(printf '%s\n' "$blocked_list" | sed '/^$/d' | wc -l | tr -d ' ')
    broken=$(failed_names | sed '/^$/d' | sort -u | paste -sd, - | sed 's/,/, /g')
  fi
  if [ -n "$broken" ]; then
    signature="$head $broken"
    if [ "$signature" != "$notified_checks" ]; then
      notify "$owner" "PR $slug: failing required check(s) on ${head:0:7}: $broken. Read the failing step, fix the cause, push once." \
        && notified_checks="$signature"
    fi
  else
    notified_checks=""
  fi

  # The branch is behind its base: updating it is the owner's work.
  if [ "$merge_state" = "BEHIND" ]; then
    signature="$head behind"
    if [ "$signature" != "$notified_behind" ]; then
      notify "$owner" "PR $slug is behind origin/$base on ${head:0:7}. Update the branch (merge origin/$base into the head), then let the checks run." \
        && notified_behind="$signature"
    fi
  else
    notified_behind=""
  fi

  # Ready for review: pr-ready is the authority, and it repeats every check plus
  # the merge. Only asked when the cheap signals are already clean, and only
  # when GitHub has not approved the PR.
  if [ -z "$pending" ] && [ "$blocked" -eq 0 ] && [ "$decision" != "APPROVED" ] \
      && [ "$merge_state" != "BEHIND" ]; then
    ready_out=$(timeout "$read_timeout" pr-ready "$pr" --repo "$repo" --root "$root" --no-wait 2>&1)
    rc=$?
    if [ "$rc" -eq 0 ] && printf '%s\n' "$ready_out" | grep -q '^READY:'; then
      signature="$head"
      if [ "$signature" != "$notified_ready" ]; then
        notify "$owner" "PR $slug is ready for the person's review — $url (head ${head:0:7}: merges cleanly into origin/$base, required checks green, no unanswered threads). Relay it: the review is the only step left, and this watcher will not approve, resolve or merge." \
          && notified_ready="$signature"
      fi
    else
      if ! printf '%s\n' "$ready_out" | grep -q '^BLOCKED:'; then
        reason=$(printf '%s\n' "$ready_out" | tail -1)
        warn "pr-ready gave no verdict${reason:+ — $reason}"
      fi
      notified_ready=""
    fi
  else
    notified_ready=""
  fi

  sleep "$interval"
done
