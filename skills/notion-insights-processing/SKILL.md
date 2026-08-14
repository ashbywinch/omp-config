---
name: notion-insights-processing
description: |
  Process raw inputs from the Notion Insights database — triage, categorize,
  route to Value Streams or Epics via proper database relations.
---

# Insights Processing

Transform raw inputs from the Notion Insights database into structured, actionable work items.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management` — database IDs live there)

## Critical Rules

### External System Rule (CRITICAL)
Writes follow the Write Permission Gate in `skill://notion-database-management` (general form: APPEND_SYSTEM.md "External Writes"). Insights-specific: an item's write list is the link AND its Status update to "Processed"; routing into a new Epic or Value Stream needs creation approval before link approval.

### Notion Reference Rule
When user says "Epic 1" or "Task 5", these refer to Notion records — not local files.

### Routing Rule
Proactively suggest routing destinations. Don't ask "where should this go?" — provide concrete suggestions. But NEVER write without explicit confirmation. Routing decisions follow the org model in `skill://business-org-model`.

### Parentage Rule
See `skill://epic-quality-standard` for the top-level-page rule (top-level = life goals + C-suite value streams only; every epic has exactly one parent) and `skill://business-org-model` for routing.

- **Prefer an existing, deep, related parent** over creating a new Epic or Value Stream. Before proposing a new Epic/VS, check the existing tree for a phase-named sub-epic with a concrete deliverable that already covers the item (e.g. a capture-pipeline epic, not the parent app epic).
- **New Epics must be parented immediately** — exactly one of Parent Epic / Parent Value Stream, never both, never neither. When creating, set the parent link in the same write as the creation; a new Epic that needs a child Epic of its own gets the child first, then the link.
- **Sub-epics are named after a phase of the project with a concrete deliverable** — not after the item itself, and not the generic parent name.
- If the only candidate parent is a Value Stream with the same name as an Epic, prefer the Value Stream (it is the standing home); flag the naming collision for the user.

### Relation Fields
Dual pairs — write the insight side, the parent side syncs (see `skill://notion-database-management`):
- insight→epic: insight **"Parent Epic"** ↔ epic **"Insights 1"**
- insight→VS: insight **"Parent Value Stream"** ↔ VS **"Insights"**
- Always refer to records using both ID and name: "1. PA Engagement Plans"

### Status Update
After processing, update Status to **"Processed"** — otherwise it appears unprocessed next session.

### Process One at a Time
Process insight items one by one, not in batch. For each item: present the routing → if the destination is a new Epic or Value Stream, get explicit approval to create it first and create it → wait for an explicit yes to that item's write list (link + Status) → write the link → update Status. Batch processing is allowed only after one explicit "process all of the above as listed" from the user, given after the full enumerated list of every item's writes (links, Status updates, any creations) has been presented — the list is the writes, not the routing suggestions. The single statement approves each enumerated write individually, so a creation approval never authorizes its link; execute creations before the links that point to them.

### Approval Language
- **"Yes to everything"** (or "yes to all", "process all") given *after* the full enumerated write list IS approval of that list.
- **"Carry on", "continue", "go ahead", "proceed", or a bare nudge IS NOT approval.** These are harness-recovery prompts meaning "start thinking again" after a glitch — the enumerated write list still needs an explicit yes.
- When in doubt about whether a statement approves the writes, restate the write list and ask for the explicit yes; never execute on an ambiguous continuation.

### Read the Full Item Before Proposing
Always fetch and read the complete item — Content, Context, Summary, and Source fields — before suggesting a routing. Items routinely contain multiple distinct tasks, hidden context, or self-located routing hints ("this is about epic X"); proposing from a truncated preview produces wrong destinations. When the note names a destination, verify it exists in Notion before proposing it.

## Process

### 1. Fetch Unprocessed Insights
Unprocessed = **unlinked**: query the Insights DB for items with no `Parent Epic` AND no `Parent Value Stream` relation, and Date Deleted empty (see `skill://notion-database-management` for query syntax). Linking the insight is the processing step — Status "Processed" is a convenience marker, not the source of truth.

### 2. Process Each Insight (One by One)
For each insight:
1. Read the full item (see "Read the Full Item Before Proposing")
2. Suggest a specific routing destination (Epic or Value Stream)
3. Follow the per-item approval sequence in "Process One at a Time" above (creation approval → write-list approval → link → Status)
4. Write the insight's `Parent Epic` or `Parent Value Stream` (child side; the parent syncs — see `skill://notion-database-management`)
5. Update Status to "Processed"

### 3. Confirm
- [ ] Insight has a parent link (Parent Epic and/or Parent Value Stream)
- [ ] Bidirectional: parent side re-read shows the insight
- [ ] Status updated to "Processed"

## Scope Boundary
Only process unprocessed, non-deleted items. Don't suggest cleanup unless asked.
