---
name: session
description: |
  Standardised wrapper for session execution — lifecycle, role adoption and
  completion. Runs the skill the calendar block names.
---

# Session Playbook

Standardised wrapper for session execution. It runs the lifecycle around the
skill the block names, and never chooses one itself.

## Resolving the block

A session is the calendar block it was scheduled as. The block's **title is the
name of the skill that runs it**, written in words: `Backlog Grooming` is
`skill://backlog-grooming`. Resolve the title to a skill and read that skill's
description to confirm it is the one meant.

A block titled with a task — `Task X`, or the task's own name — is that task: the
work is the task itself, and no skill is started.

If nothing resolves, or two candidates do, ask the user which skill the block is
for. Never pick one, and never start a skill the title does not name.

## Parameters

- **Session Type** (required): the calendar block's title (`skill://google-calendar`)
- **Skill** (required): resolved from the title, or named by whoever starts the
  session
- **Session Definition** (optional): Timing, objectives, constraints from the caller

## Process

### 1. Session Setup

- **Validate the Skill**: Confirm the named skill exists
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
