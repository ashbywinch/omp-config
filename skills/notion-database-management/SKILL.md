---
name: notion-database-management
description: |
  Core Notion operations via the `ntn` CLI — auth, query patterns, page CRUD,
  property types, error recovery. Domain skills reference this for API mechanics.
---

# Notion Database Management

Core patterns for Notion operations via `ntn`. Domain skills reference this for API mechanics rather than inlining them.

## Prerequisites

- `ntn` installed (`curl -fsSL https://ntn.dev | bash`)
- Authenticated: `ntn login --no-browser` → user confirms in browser → `ntn login poll`

**Token alternative:** Set `NOTION_API_TOKEN` env var instead of browser login. The token takes precedence over keychain auth.

**Session expired mid-session?** Re-run `ntn login --no-browser` and poll again. Tokens last ~1 hour.

## Write Permission Gate (CRITICAL)

The general rule is APPEND_SYSTEM.md "External Writes" — apply it to every create, PATCH, delete, and relation change in every database. Notion-specific additions:

- **Create and link are separate approvals.** Routing an insight into a new epic needs (1) approval to create the epic, then (2) approval of the link. A creation approval never authorizes the link.
- **Every write needs enumerating, including Status updates.** A "mark as processed"-style PATCH is a write like any other and belongs in the approved list.

## Database IDs

| Database | ID |
|---|---|
| Epics | `20d3122e-1a13-81a1-8388-de5cebd1acb2` |
| Tasks | `20d3122e-1a13-813a-9231-e7e086b2b86f` |
| Insights | `20d3122e-1a13-8110-b1c2-fa15ecadde25` |
| Value Streams | `20d3122e-1a13-81be-8412-e536c02f77d4` |
| Missions | `20d3122e-1a13-8147-9b53-c6c04bd99926` |

## Query Patterns

### Preferred: datasources query (cleaner output)
```bash
ntn datasources query <DATA_SOURCE_ID> --limit 50
ntn datasources query <DATA_SOURCE_ID> --limit 10 --json  # includes full properties
ntn datasources query <DATA_SOURCE_ID> --filter '{"property":"Status","select":{"equals":"Draft"}}'
ntn datasources query <DATA_SOURCE_ID> --filter '{"property":"Status","select":{"is_empty":true}}'  # empty select
ntn datasources query <DATA_SOURCE_ID> --limit 50 --json --start-cursor <CURSOR>  # paginate; the flag is --start-cursor, not --cursor
```

To find a data source ID, retrieve the database:
```bash
ntn api v1/databases/<DATABASE_ID> | jq -r '.data_sources[0].id'
```

### Fallback: raw API (for sort, filter_properties, pagination)
```bash
echo '{"page_size":10,"sorts":[{"property":"Epic ID","direction":"ascending"}]}' | \
  ntn api v1/databases/<DATABASE_ID>/query
```

## Page CRUD

### Create a page in a database
Always use **stdin JSON** — never inline body fields (avoids escaping issues):
```bash
cat <<'JSON' | ntn api v1/pages
{
  "parent": {"database_id": "<DATABASE_ID>"},
  "properties": {
    "Epic Name": {"title": [{"text": {"content": "Epic Title"}}]},
    "Status": {"select": {"name": "Draft"}}
  }
}
JSON
```

**Capture the page ID immediately after creation** (output gets truncated):
```bash
cat <<'JSON' | ntn api v1/pages | jq -r '.id'
{...}
JSON
```

### Read a page
```bash
ntn api v1/pages/<PAGE_ID> | jq '.properties'
```

### Update page properties
```bash
echo '{"properties": {"Status": {"select": {"name": "Completed"}}}}' | \
  ntn api v1/pages/<PAGE_ID> -X PATCH
```

### Update page content (markdown body)
```bash
echo "Updated content" | ntn pages edit <PAGE_ID>
```

## Key Rule: Use Property Names, Not Internal IDs

Notion properties have both a **display name** (e.g. `"Status"`) and an internal property ID (e.g. `"Q%5B%3FR"`). Always use the display name in API calls. Using internal IDs causes "Couldn't find editable properties" errors.

**Wrong:** `{"Q%5B%3FR": {"select": {"name": "Draft"}}}`

**Correct:** `{"Status": {"select": {"name": "Draft"}}}`

**If a property name doesn't work**, the actual name may differ from what you expect (e.g. `"Related to Epics"` may actually be `"Related to Epics (Related Tasks)"`). Check the data source schema:
```bash
ntn api v1/data_sources/<DATA_SOURCE_ID> | jq '.properties | keys'
```

## Property Type Reference

| Type | JSON Shape |
|---|---|
| **Title** | `{"title": [{"text": {"content": "Page Title"}}]}` |
| **Rich text** | `{"rich_text": [{"text": {"content": "value"}}]}` |
| **Select** | `{"select": {"name": "OptionName"}}` |
| **Number** | `{"number": 42}` |
| **Relation** (set) | `{"relation": [{"id": "target-page-id"}]}` |
| **Relation** (clear) | `{"relation": []}` |
| **Date** | `{"date": {"start": "2026-07-28"}}` |

**Always clear the Parent Epic field on top-level items** — otherwise they show up as children of whatever was last in the relation array:
```json
"Parent Epic": {"relation": []}
```

## Relation Write Rule (CRITICAL)

**A relation PATCH replaces the whole array — it does not append.** Entries MUST be `{"id": "..."}` objects — bare strings fail validation.

**Multi-value appends on dual pairs are child-side writes.** For a dual-pair relation (insight↔epic, insight↔VS, task↔epic, epic↔epic, epic↔VS, VS↔VS), write the CHILD side and let the parent array sync — never patch the parent side. A child-side PATCH on a multi-valued child field must contain the full desired array (a single-ID write drops the child's other links). Read-modify-write applies only to relations with no child-side field (e.g. an epic's `Dependencies`): read the page first, build the full array (existing IDs + new ID(s)), PATCH with the complete array. **NEVER PATCH with only the new ID** — a relation PATCH replaces the whole array, so a single-ID write silently drops every existing link.

**Read at write time, never from a snapshot.** Read the live page (`ntn api v1/pages/<PAGE_ID>`) immediately before each PATCH — never a session-start or shared `/tmp` file, which is stale the moment another session writes.

**Never silence a relation write.** No `> /dev/null`: re-read the page after the PATCH and confirm the array length is exactly existing + new.

**Rich-text fields replace too.** PATCHing `Content` (or any rich_text property) replaces the WHOLE property — appending to a multi-block ticket means re-sending all existing blocks. Never PATCH `Content` with only the new text.

**Moving an item between pages** (e.g. re-parenting an insight or task): write the CHILD side only — the dual sync updates both parents (new parent gains, old parent drops). Verify both parents' child-side arrays after; if one is stale, correct that side.

**Dependencies**: live in the dedicated `Dependencies` relation field on Epics. Value Streams should have one too — flag it if the schema lacks it. Never store dependencies in Processing Notes; an insight-level dependency surfaces when its epic or task is created.

**Parent links** (`Parent Epic`, `Parent Value Stream` on a child page): single-value, written fresh on the child. The dual-property sync populates the parent's child-side field (`Child Epics` / `Child Value Streams`) automatically — write the child side, verify both sides, never hand-maintain the parent's child field.

## Parent-child relations (dual property pairs)

Hierarchies use **dual property pairs** — one field per direction, synced automatically:

| Relation | Child side | Parent side |
|---|---|---|
| epic→epic | `Parent Epic` | `Child Epics` |
| epic→VS | `Parent Value Stream` | `Child Epics` (on the VS) |
| VS→VS | `Parent Value Stream` | `Child Value Streams` |
| task→epic | `Related to Epics (Related Tasks)` | `Related Tasks` |
| insight→epic | `Parent Epic` | `Insights 1` |
| insight→VS | `Parent Value Stream` | `Insights` (VS) |

- A page's own `Parent Epic` / `Parent Value Stream` field contains **only its parent**; its `Child Epics` / `Child Value Streams` field contains **only its children**. Never mixed.
- **Write the parent link on the CHILD side** (`child.ParentEpic = [parent]`) — the dual sync populates the parent's `ChildEpics` automatically. Writing either side of a pair populates both; never hand-maintain both sides.
- **Never clear or replace a parent's child-side array** (`ChildEpics` / `Child Value Streams`) to "clean up" — and never write children into a page's own `ParentEpic` field. Clearing a page's `ParentEpic` removes its own parent link, which also removes it from its parent's `ChildEpics`.
- **Verify after any parent-link write**: re-read and confirm both sides of the pair (child's parent field AND parent's child field).
- **Reading the tree**: parentage resolves from the child side (pages whose `Parent Epic` contains the parent). A page's own fields are unambiguous now, but child-side is still the reliable source for building trees.

## Link Audit (detecting lost links)

An insight is linked if its ID appears in any epic's `Insights 1` or any VS's `Insights` array. To find orphans: fetch all three collections, collect every relation ID, then list processed insights whose ID is in none.

## Bulk Writes (pacing)

Bursts of rapid PATCHes stall under Notion rate limiting (calls hang ~15s or time out). For bulk link/migration loops: space calls ~1-2s apart, wrap each call in a per-call timeout, retry with backoff (3-5 attempts), and log progress per write — never fire a silent un-paced loop.

**ID hygiene in bulk operations**: resolve every ID from fresh data by name — never reuse a remembered ID (a mis-remembered ID re-parents the wrong page); when multiple sources map to one target (e.g. two epics folding into one VS), dedupe the target set before creating; after a batch of creates, verify name-uniqueness — duplicate pages with the same name are the failure signature.

## Error Recovery

| Problem | Fix |
|---|---|
| `No auth token found` | Re-run `ntn login --no-browser` → poll |
| `400 validation_error` | Check property names are the **display name**, not the internal ID |
| JSON response truncated | Extract ID at creation time with `| jq -r '.id'` |
| Can't find data source ID | `ntn api v1/databases/<DB_ID> \| jq -r '.data_sources[0].id'` |
| Wrong parent on a page | PATCH with `{"Parent Epic": {"relation": []}}` to clear, or the correct ID to set |
