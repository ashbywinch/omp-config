---
name: prod-deploy-via-release-only
description: Production changes go ONLY through the project's release process; ad-hoc commands on a host are never a deployment path. If the process is too slow, improve it — never bypass it.
---

# Production deploy via the release process only

A production change — code, schema, config, restart — is deployed through
the project's **defined release process** (its CI/release workflow, or the
release scripts that workflow invokes). Ad-hoc shell commands on a
production host (pull + restart, direct config edits, manual restarts) are
**not** a deployment path, however urgent the fix feels. If the release
process is too slow or awkward to use, the answer is to improve the
process, never to bypass it.

## Why

The release process exists to make production changes reviewable, tested
(standby + smoke before switch), and reversible (rollback). Every ad-hoc
bypass erodes that: an unreviewed change ships, the smoke gate is skipped,
rollback is impossible, and the next person (or agent) follows the
precedent.

## Mechanical enforcement, not just documentation

A rule that only says "don't" gets broken under pressure. The durable
guard is permissions: on the production host, the deploy user's elevated
access is restricted to exactly the release scripts (a sudoers rule, or
equivalent); no interactive login can restart the app units or mutate the
deployment directly. Then a direct deployment is not merely discouraged —
it is impossible. Read-only diagnostics (logs, status) stay available.

## Guardrails

- Deploy via the workflow/release script, or don't deploy.
- A broken release process is a blocker to fix; skipping it is never the fix.
- Host permissions make direct mutation impossible; verify the guard works
  (attempt the blocked operation and confirm it fails).
- One-time infrastructure hardening (permissions, keys) that makes the
  guard real is legitimate — do it deliberately, verify it, and record it
  in the reproducible setup so fresh hosts get the guard automatically.
