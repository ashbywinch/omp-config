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

Structural questions start with `query_graph` — one pattern per question:

- who calls this — `callers_of`
- who imports this — `importers_of`
- what does this file contain — `file_summary`
- what overrides this — `inheritors_of`
- what does this call — `callees_of`
- which tests cover this — `tests_for`
- what are its children — `children_of`

Run it before any text search: the graph is parsed AST and finds callers a
text regex misses (renamed parameters, re-exports). grep/read come after —
once the graph has located the exact file and line, use them to read the
file's contents. This rule takes precedence over any conflicting
grep/search instructions.

## Impact analysis

Before editing a function others call, run `get_impact_radius` (and
`query_graph` with `callers_of`) — the first row of the table below. Do
not treat blast radius as a veto: impact analysis informs where you test,
not whether you make the change.

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
the watcher is running. Nothing reports the watcher's downtime, so treat
staleness as possible after any switch and run this sequence once:

1. **Detect** — `code-review-graph status`. A branch WARNING or a built
   commit ≠ HEAD means the graph is stale. (A watcher that was down
   during a switch recovers nothing when restarted — it is purely
   event-driven, with no startup sweep; only `build` recovers.)
2. **Recover** — `code-review-graph build`: incremental; re-parses only
   files whose stored hash differs from disk. `build` is standalone — it
   reads the working tree directly and needs no watcher. If `build`
   errors, or `status` still reports stale afterwards, check file
   permissions and graph-state corruption first; `--full-rebuild` is the
   last resort for confirmed corrupt state — never routine (it discards
   the incremental fast path).
3. **Verify** — re-run `status`: the signal from Detect must be gone
   before trusting graph answers.

**When to trust the graph:** only after step 3 (or a `status` with no
WARNING and a built commit equal to HEAD). When graph answers contradict
the code you are reading, suspect the graph first and run the sequence
before distrusting the code.
