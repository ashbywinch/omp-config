"""Called by .github/workflows/pr-agent.yml — fail the PR if the review bot
did not post a "PR Reviewer Guide" comment covering the head commit.
The review may have failed silently; this check prevents merging unreviewed.
"""

import json
import os
import sys
import urllib.request


def main() -> int:
    sha = os.environ["SHA"]
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["PR_NUMBER"]
    token = os.environ["GITHUB_TOKEN"]

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    comments = json.load(urllib.request.urlopen(req))
    covered = any(
        c.get("body", "").startswith("## PR Reviewer Guide") and sha in c.get("body", "")
        for c in comments
    )
    if not covered:
        print(f"::error::AI review did not post for commit {sha} — the review may have failed silently.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
