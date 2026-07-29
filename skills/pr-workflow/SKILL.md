---
name: pr-workflow
description: |
  GitHub Pull Request creation workflow — validate changes, create PR
  description with full change scope, push and create via gh CLI.
---

# GitHub PR Creation

Create properly formatted GitHub Pull Requests.

## Prerequisites

- `gh` CLI installed and authenticated
- All work committed on a feature branch (not main)

## Process

### 1. Change Validation
```bash
git status                     # must be clean
git diff main --name-only      # every file changed
git log --oneline main..HEAD   # every commit
```

Never rely on memory — check the actual diff.

### 2. Push Feature Branch
```bash
git branch                     # confirm not on main
git push origin <branch-name>
```

### 3. Create PR Description
Create a `pr_description.md` file in the current directory with:
- Architecture/Main Theme
- Key Changes (grouped logically)
- Insights Created
- Testing Performed
- Related issues

### 4. Create PR
```bash
gh pr create \
  --title "type: description" \
  --body-file pr_description.md \
  --base main \
  --head <branch-name>
```

### 5. Clean Up
```bash
rm pr_description.md
```

## Constraints

- CAN create PRs, add comments, request reviews
- CANNOT approve or merge PRs
- CANNOT override branch protection rules

## Success Criteria
- PR description captures all changes with context
- Human reviewer can understand without additional info
- Branch protection prevents unauthorized merging
