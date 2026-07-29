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

## Database IDs

| Database | ID |
|---|---|
| Epics | `20d3122e-1a13-81a1-8388-de5cebd1acb2` |
| Tasks | `20d3122e-1a13-813a-9231-e7e086b2b86f` |
| Insights | `20d3122e-1a13-8110-b1c2-fa15ecadde25` |

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

## Error Recovery

| Problem | Fix |
|---|---|
| `No auth token found` | Re-run `ntn login --no-browser` → poll |
| `400 validation_error` | Check property names are the **display name**, not the internal ID |
| JSON response truncated | Extract ID at creation time with `| jq -r '.id'` |
| Can't find data source ID | `ntn api v1/databases/<DB_ID> \| jq -r '.data_sources[0].id'` |
| Wrong parent on a page | PATCH with `{"Parent Epic": {"relation": []}}` to clear, or the correct ID to set |
