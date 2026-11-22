#!/bin/bash
# Fetch all PR findings (inline comments, issue comments, review threads)
# with FULL comment bodies — never truncated. Works from any repo.
# Usage: fetch-pr-findings.sh <PR-number>
#
# The tally is printed before the bodies for one reason: a bare `gh api`
# returns 30 items per page and reads as the whole list, so a human's comment
# can sit past the page boundary and look absent. The tally pages in full and
# marks every person with `*`, so "nobody human spoke" is checkable.
set -euo pipefail
n="${1:?usage: fetch-pr-findings.sh <PR-number>}"
repo="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

tally() {
  local label="$1" path="$2" counts
  counts=$(gh api --paginate "$path" \
    --jq '.[] | .user.login + (if .user.type == "Bot" then "" else "*" end)' \
    | sort | uniq -c | awk '{printf "%s×%s  ", $2, $1}' | sed 's/  *$//')
  printf '%-8s %s\n' "$label" "${counts:-none}"
}

echo "=== TALLY (paged in full; * marks a person) ==="
tally inline "repos/$repo/pulls/$n/comments"
tally issue "repos/$repo/issues/$n/comments"

echo "=== INLINE (pulls/$n/comments) ==="
gh api --paginate "repos/$repo/pulls/$n/comments" \
  --jq '.[] | "---\n\(.user.login) @ \(.path):\(.line // .original_line) [id:\(.id)]\n\(.body)\n"'
echo "=== ISSUE (issues/$n/comments) ==="
gh api --paginate "repos/$repo/issues/$n/comments" \
  --jq '.[] | "---\n\(.user.login) @ \(.created_at)\n\(.body)\n"'
echo "=== REVIEWS (pull request reviews) ==="
gh pr view "$n" --repo "$repo" --json reviews \
  --jq '.reviews[] | "---\n\(.author.login) (\(.state))\n\(.body)\n"'
