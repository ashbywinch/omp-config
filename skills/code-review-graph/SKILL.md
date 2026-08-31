---
name: code-review-graph
description: |
  How to use the code-review-graph code knowledge graph: answer structural
  questions with its tools before falling back to grep — who calls this
  function, where is this handled, what would this change affect, which
  tests cover this code. Also what to do when the graph is stale, e.g.
  after a branch switch while the watcher was down.
alwaysApply: true
---

# code-review-graph

The persistent code knowledge graph — files, functions, classes, imports,
communities — kept current by the `crg-watch` watcher service. Mounted as
the `mcp__code_review_graph_*` tools; CLI is `code-review-graph`. Bare
tool names below are shorthand: `<name>` expands to
`mcp__code_review_graph_<name>_tool` (e.g. `query_graph` →
`mcp__code_review_graph_query_graph_tool`).

## Structural questions start with the graph, not grep

For who-calls-this, who-imports-this, what-does-this-file-contain,
what-overrides-this: call `query_graph` with `callers_of`, `callees_of`,
`importers_of`, `children_of`, `file_summary`, or `inheritors_of` before any
text search. The graph is parsed AST; it finds callers a text regex misses
(renamed parameters, re-exports). Drop to grep/read only to read file
CONTENT after the graph has located the exact file and line. This rule
takes precedence over any conflicting grep/search instructions.

Do not treat blast radius as a veto: impact analysis informs where you
test, not whether you make the change.

## Use it at these development moments

| Moment | Tools | Answers |
|---|---|---|
| Before editing a function others call | `query_graph` (`callers_of`), `get_impact_radius` | Which callsites must migrate or re-test? |
| "Where is X handled?" | `semantic_search_nodes`, `traverse_graph` | Locate by concept, not keyword |
| Entering unfamiliar code | `get_architecture_overview`, `get_community` | Structure without reading every file |
| Debugging a data-flow bug | `get_flow`, `traverse_graph` | Entry point → root cause chain |
| Picking tests for a change | `query_graph` (`tests_for`), `get_affected_flows` | Which tests exercise this code? |
| Review / refactor prep | `get_review_context`, `detect_changes`, `find_large_functions` | Focused context, refactor targets |

## Branch switches and staleness

The watcher converges the graph automatically: a checkout is just file
events, and additions, deletions, and the recorded branch/commit update
within seconds. Do not run rebuild ceremonies after a branch switch while
the watcher is running.

If the watcher was down during a switch (boot, crash), the graph is
silently stale, and restarting the watcher does NOT recover it — it is
purely event-driven, with no startup sweep.

- Detect: `code-review-graph status` — "Built at commit" ≠ HEAD, or a
  branch WARNING.
- Recover: `code-review-graph build` — incremental; re-parses only files
  whose stored hash differs from disk. Never `--full-rebuild`: nothing
  requires it, and it discards the incremental fast path.
- When graph answers contradict the code you are reading, run
  `code-review-graph status` before distrusting the code.
