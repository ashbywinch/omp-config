---
name: code-discovery
description: Use code-review-graph before grep for structural code discovery
alwaysApply: true
---

## Code Discovery Rules

For ALL structural code discovery — finding files, symbols, callers, callees,
importers, or any cross-file relationship — you MUST use the code-review-graph
MCP tools FIRST:

- `mcp__code_review_graph_query_graph_tool` with patterns: `callers_of`, `callees_of`,
  `importers_of`, `imports_of`, `file_summary`, `inheritors_of`, `children_of`
- `mcp__code_review_graph_traverse_graph_tool` for free-form exploration
- `mcp__code_review_graph_get_review_context_tool` for impact analysis

Use `grep`, `read`, or `bash` ONLY after the graph has located the exact file
path, symbol name, and line number. grep is for reading file content — never
for finding where something lives or what calls what.

The graph operates on parsed AST and never misses patterns that text regex
would. A file watcher (`code-review-graph watch`) keeps it up to date automatically
— no manual build step needed.

This rule takes precedence over any conflicting grep/search instructions.
