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

**A relation PATCH replaces the whole array — it does not append.** Two cases:

**Multi-value appends** (e.g. a second insight to an epic's `Insights` field): read the page first, build the full array (existing IDs + new ID(s)), PATCH with the complete array. Never PATCH with only the new ID — it silently drops the existing links.

**Parent links** (`Parent Epic`, `Parent Value Stream` on a child page): single-value, written fresh on the child. Read the child's current field only to preserve its own parent (a child has exactly one parent); never use a parent page's mirrored array as the source of truth, and never PATCH a parent's field to adjust children — that drops the mirrored child links.

## Parent-field Mirroring

Notion relations are **natively bidirectional** — setting a relation on one side auto-creates the back link on the other. There is no manual back-link maintenance: never PATCH both sides of the same relation.

- **Write the parent link on the CHILD page** — the child points up at its parent. Notion mirrors the entry onto the parent's field automatically.
- **Never hand-maintain a parent's relation array** to "add" or "clean up" back links. The parent's field legitimately contains both its own parent AND its children (mirrored); replacing that array is destructive — it silently drops the mirrored child links (a real failure mode: re-parenting a page dropped its child's link entirely).
- **When reading**: if a page's `Parent Epic` field shows pages that point back at it, those are its children, not its parent — ignore them. Reading a page's own `Parent Epic` field cannot distinguish parent from mirrored child; resolve parentage from the child-side links or numbering.
- **After any parent-link write, verify**: re-read the parent page and confirm the child appears as a back link. If the mirror is missing, re-set the forward link on the child (don't patch the parent).
- **Mirroring direction is not symmetric in practice (observed 2026-08-10)**: for epic→VS relations, writes made from the **VS side** (the synced `Related to Epics` field) populate both sides, but writes from the epic's `Parent Value Stream` side did NOT populate the VS mirror. When back-filling or repairing epic→VS links, write from the VS side. (Epic→epic `Parent Epic` relations mirrored correctly from the child side in the same session.)
- **Hierarchy semantics** live in `skill://epic-quality-standard` (exactly one of `Parent Epic` / `Parent Value Stream` per epic, never both).

## Error Recovery

| Problem | Fix |
|---|---|
| `No auth token found` | Re-run `ntn login --no-browser` → poll |
| `400 validation_error` | Check property names are the **display name**, not the internal ID |
| JSON response truncated | Extract ID at creation time with `| jq -r '.id'` |
| Can't find data source ID | `ntn api v1/databases/<DB_ID> \| jq -r '.data_sources[0].id'` |
| Wrong parent on a page | PATCH with `{"Parent Epic": {"relation": []}}` to clear, or the correct ID to set |
