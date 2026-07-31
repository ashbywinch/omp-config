---
description: When a computation produces unexpected results, use logs, traces, and diagnostic chains to find the root cause — never delete state, clear caches, or restart systems as a first step.
---

# Use Observability Before Corrective Action

When you see wrong or surprising output, the evidence is in the system's observability. Gather it before taking any action that would destroy it.

## First: read the traces

- Check logs for errors, warnings, and API responses near the relevant timestamps.
- Follow provenance chains — each node's persisted result includes its provenance label and (after fix) its deps' provenance. A node failing with "dep failed: X" means node X failed first — check X's result.
- Query the database to read node results, not to delete them.

## Never as a first step

- **Delete database rows** — this destroys the evidence of what happened. The in-memory objects were already constructed from those rows; deleting them doesn't change in-memory state anyway.
- **Clear caches** — you lose the difference between a cache-hit and a cache-miss.
- **Restart the server** — you lose in-memory state that could explain transient failures.
- **Reseed/reimport data** — you overwrite the state that produced the wrong output.

## When you've found the root cause

Fix the code. Then the fix deploys (auto-reload, restart, etc.) as part of the normal process — not as a debugging step.

## The provenance chain IS the debugger

Every DAG node's `to_json()` output includes its provenance. Start at the node with the wrong value, read its provenance, then read each dep's provenance in turn. You'll trace back to the source of the error:
- An API call that returned an unexpected response
- A dep that itself is impossible with an explanatory error
- A cache key collision producing a stale value
