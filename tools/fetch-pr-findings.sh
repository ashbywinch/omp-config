#!/bin/bash
# Fetch all PR findings (inline comments, issue comments, review threads)
# with FULL comment bodies — never truncated. Works from any repo.
# Usage: fetch-pr-findings.sh <PR-number>
set -euo pipefail
n="${1:?usage: fetch-pr-findings.sh <PR-number>}"
repo="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
echo "=== INLINE (pulls/$n/comments) ==="
gh api --paginate "repos/$repo/pulls/$n/comments" \
  --jq '.[] | "---\n\(.user.login) @ \(.path):\(.line)\n\(.body)\n"'
echo "=== ISSUE (issues/$n/comments) ==="
gh api --paginate "repos/$repo/issues/$n/comments" \
  --jq '.[] | "---\n\(.user.login) @ \(.created_at)\n\(.body)\n"'
echo "=== REVIEWS (pull request reviews) ==="
gh pr view "$n" --json reviews \
  --jq '.reviews[] | "---\n\(.author.login) (\(.state))\n\(.body)\n"'