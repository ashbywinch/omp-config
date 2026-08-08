---
name: notion-insights-processing
description: |
  Process raw inputs from the Notion Insights database — triage, categorize,
  route to Value Streams or Epics via proper database relations.
---

# Insights Processing

Transform raw inputs from the Notion Insights database into structured, actionable work items.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Insights DB ID: `20d3122e-1a13-8110-b1c2-fa15ecadde25`

## Critical Rules

### External System Rule (CRITICAL)
NEVER write to any Notion database without explicit user approval of the exact write. The Write Permission Gate in `skill://notion-database-management` is the normative rule: enumerate every intended write, wait for an explicit yes to that list, never create records by inference, never bundle writes into an answer to a question, and treat discussion or design talk as NOT approval. Routing into a new Epic or Value Stream requires two approvals: the record's creation first, then the link.

### Notion Reference Rule
When user says "Epic 1" or "Task 5", these refer to Notion records — not local files.

### Routing Rule
Proactively suggest routing destinations. Don't ask "where should this go?" — provide concrete suggestions. But NEVER write without explicit confirmation.

### Relation Fields
- **Epics** use **"Insights"** relation field (not legacy "Key Insights" text field)
- **Value Streams** use **"Key Insights 2"** relation field
- Always refer to records using both ID and name: "1. PA Engagement Plans"

### Status Update
After processing, update Status to **"Processed"** — otherwise it appears unprocessed next session.

### Process One at a Time
Process insight items one by one, not in batch. For each item: present the routing → wait for the user's confirmation of THAT item → write the link → update Status. Batch processing is allowed only after one explicit "process all of the above as listed" from the user, given after the full enumerated list has been presented.

## Process

### 1. Fetch Unprocessed Insights
Query the Insights DB for items where Status is empty and Date Deleted is empty (see `skill://notion-database-management` for query syntax).

### 2. Process Each Insight (One by One)
For each insight:
1. Read the raw text
2. Suggest a specific routing destination (Epic or Value Stream)
3. Wait for user confirmation of THAT item — discussion of the routing is not confirmation
4. If the destination is a new Epic or Value Stream: get explicit approval to create it first, create it, then link
5. Link via relation (see `skill://notion-database-management` for relation PATCH syntax)
6. Update Status to "Processed"

### 3. Confirm
- [ ] Routed to appropriate Epic or Value Stream
- [ ] Status updated to "Processed"
- [ ] Relations properly linked

## Scope Boundary
Only process unprocessed, non-deleted items. Don't suggest cleanup unless asked.
