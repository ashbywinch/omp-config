---
description: After making code changes, offer to create a pull request; before reporting a PR's state, load skill://pr-workflow and run watch-pr.sh.
---

# PR After Changes

When files have been modified and the work unit is complete:

1. Check if all changes are committed on a feature branch (not main)
2. Offer to create a PR using `skill://pr-workflow`
3. Do not create the PR without explicit user approval
4. **Before reporting any PR's state** (ready / blocked / mergeable), load
   `skill://pr-workflow` and run `watch-pr.sh <n>`. Green checks and
   `mergeable` are not readiness: an unanswered review thread means
   **awaiting reply**, never "ready".
