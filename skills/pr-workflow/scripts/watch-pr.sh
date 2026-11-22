#!/usr/bin/env bash
# Watch a pull request and exit when there is something to do.
#
#   watch-pr.sh <pr> [required-check] [interval-seconds]
#
# Two exits, both actionable:
#   NEW THREADS …  — the reviewer is the last voice on a thread; each file:line
#                    is printed. Answer them, then run this again.
#   READY <sha>    — a verdict from *after* the review, not before it.
#
# READY requires ALL of these across two consecutive polls:
#   * every workflow run for the head completed, and the head's AI Code Review
#     run completed — a review is an asynchronous event that posts after the
#     checks close, so checks alone are a verdict from before the findings;
#   * every check-run completed and the required check success;
#   * no thread awaiting a reply, and the set of unresolved threads unchanged
#     since the previous poll.
#
# It never waits for threads to be *resolved* — only the reviewer resolves, so
# a watcher waiting on that would never return. Reply is the agent's half.
#
# The bot's login is not stable (GraphQL `github-actions`, REST
# `github-actions[bot]`), so unanswered means "the last voice is not ours" by
# prefix, never an equality test against a hardcoded name.
#
# Every test is an `if`: the harness shell runs with `errexit`, and an
# `[ … ] && break` one-liner aborts the watcher on its first false test.
set -uo pipefail

pr="${1:?usage: watch-pr.sh <pr> [required-check] [interval-seconds]}"
required="${2:-build-and-test}"
review_name="${REVIEW_WORKFLOW:-AI Code Review}"
interval="${3:-60}"

owner=$(gh repo view --json owner --jq .owner.login)
name=$(gh repo view --json name --jq .name)
me=$(gh api user --jq .login 2>/dev/null || true)
mine="${me:-omp-harness}"

query='query($o:String!,$n:String!,$pr:Int!){repository(owner:$o,name:$n){pullRequest(number:$pr){reviewThreads(first:100){nodes{isResolved path line comments(last:1){nodes{author{login}}}}}}}}'

head=""
calm=0
threads="none"

while :; do
  current=$(gh pr view "$pr" --json headRefOid --jq .headRefOid) || { sleep "$interval"; continue; }
  if [ "$current" != "$head" ]; then
    head="$current"
    calm=0
    threads="none"
    echo "head ${head:0:7}"
  fi

  state=$(gh api graphql -f query="$query" -f o="$owner" -f n="$name" -F pr="$pr" \
    --jq '[.data.repository.pullRequest.reviewThreads.nodes[]
           | select(.isResolved == false)
           | "\(.path):\(.line) last=\(.comments.nodes[0].author.login)"] | sort | .[]' 2>/dev/null) || state=""

  # The reviewer is the bot; a human resolves rather than replies. Only a
  # bot-last thread is unanswered, whatever identity our own replies carry.
  waiting=$(echo "$state" | grep -E "last=github-actions" | grep . || true)
  if [ -n "$waiting" ]; then
    echo "NEW THREADS on ${head:0:7} — answer each, then run this watcher again:"
    echo "$waiting"
    exit 0
  fi

  runs=$(gh api "repos/$owner/$name/actions/runs?head_sha=$head" \
    --jq '[.workflow_runs[] | select(.status != "completed")] | length' 2>/dev/null) || runs=1
  reviewed=$(gh api "repos/$owner/$name/actions/runs?head_sha=$head" \
    --jq '[.workflow_runs[] | select(.name == "'"$review_name"'") | select(.status == "completed")] | length' 2>/dev/null) || reviewed=0
  pending=$(gh api "repos/$owner/$name/commits/$head/check-runs" \
    --jq '[.check_runs[] | select(.status != "completed")] | length' 2>/dev/null) || pending=1
  verdict=$(gh api "repos/$owner/$name/commits/$head/check-runs" \
    --jq '[.check_runs[] | select(.name == "'"$required"'") | .conclusion] | unique | join(",")' 2>/dev/null) || verdict=""

  stable="no"
  if [ "$state" = "$threads" ]; then
    stable="yes"
  fi
  threads="$state"

  if [ "$runs" = "0" ] && [ "$reviewed" -ge 1 ] && [ "$pending" = "0" ] \
     && [ "$verdict" = "success" ] && [ "$stable" = "yes" ]; then
    calm=$((calm + 1))
    if [ "$calm" -ge 2 ]; then
      echo "READY ${head:0:7} (checks green, review posted, threads unchanged and answered)"
      exit 0
    fi
  else
    calm=0
  fi

  sleep "$interval"
done
