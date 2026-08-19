#!/bin/bash
# Fetch all PR findings (inline comments, issue comments, review threads)
# in one consolidated output. Run from the repo root.
# Usage: fetch-pr-findings.sh <PR-number>
set -euo pipefail
n="${1:?usage: fetch-pr-findings.sh <PR-number>}"
repo="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
echo "=== INLINE ===" && gh api --paginate "repos/$repo/pulls/$n/comments" \
  --jq '.[] | "\(.user.login) @ \(.path):\(.line) — \(.body[:200])"'
echo "=== ISSUE ===" && gh api --paginate "repos/$repo/issues/$n/comments" \
  --jq '.[] | "\(.user.login) @ \(.created_at) — \(.body[:200])"'
echo "=== REVIEWS ===" && gh pr view "$n" --json reviews \
  --jq '.reviews[] | "\(.author.login) (\(.state)) — \(.body[:200])"'