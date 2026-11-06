---
name: session
description: |
  Standardised wrapper for all engagement execution. Handles session lifecycle,
  role adoption, completion protocols, and integration with coordination systems.
---

# Session Playbook

Standardised wrapper for session execution. `skill://pa-coordination` routes every
scheduled session through it.

## Session Type Routing

A session is identified by the calendar block it was scheduled as: the block's
subject is the session type, its start and end are the time. Read the block from
the calendar (`skill://google-calendar`); the day plan lists the same blocks.

`skill://pa-coordination` holds the routing table: each session type and the
skill that runs it.

## Parameters

- **Session Type** (required): the calendar block's subject, a name from
  `skill://pa-coordination`'s routing table
- **Session Definition** (optional): Timing, objectives, constraints from PA Coordination

## Process

### 1. Session Setup

- **Validate Session Type**: Confirm the target skill/plan exists
- **User Profile Check**: Verify profile exists at `~/.config/omp/profiles/User Profile.md`. If missing, create one first.
- **Pre-Session Prep**: Gather any required context for the session

### 2. Role Adoption

Read the target skill/plan and adopt its expert role. For example, if the session type is backlog grooming, adopt a Scrum Master perspective.

### 3. Execute Session

Run the target skill/plan with full focus. Track progress and capture outputs.

**Watch for:**
- User corrections or process redirections — flag for later improvement
- Scope creep ("while we're at it...") — note it, stay on track
- Multi-domain expansion — may need separate sessions

### 4. Session Completion

After the target skill finishes:

1. **Change workflow**: If files were modified, commit changes and run `skill://pr-workflow`
2. **Session minutes**: Document what was accomplished, key decisions, insights
3. **Action closures**: List any follow-up items with skill references
4. **Process improvements**: If the user corrected your approach, run `skill://process-improvement`
5. **Update coordination state**: Report completion

### 5. User Correction Protocol

When the user corrects you:
- **If you agree**: Follow the instruction immediately
- **If you think the user is wrong**: State your reasoning clearly, ask clarifying questions, work through it together — never silently make opposing changes

## Success Criteria

- Target skill executed successfully
- Session documented (what was done, key decisions, follow-ups)
- Any incomplete work captured for future sessions
- User confirms satisfaction
