---
name: write-documentation
description: |
  How to write and update documentation — the process: audience questions,
  context efficiency, density craft, and the update flow. The normative
  rules live in the standards, not here: docs/writing-documentation.md
  (what good documentation is) and docs/documentation-structure.md (the
  required doc set and folder structure). Apply them; don't restate them.
---

When asked to write or update documentation, read and apply the two
standards first:

- `docs/writing-documentation.md` — what good documentation is: context
  efficiency, density, no-duplication, one topic per file, the quality
  checklist, AGENTS.md as bootloader.
- `docs/documentation-structure.md` — the required doc set and folder
  structure: PRD / TECHSPEC / PLAN and their mandated content, and the
  discoverability rule (every doc reachable from AGENTS.md).

This skill is the process around them. Writing a skill is writing
documentation: SKILL.md is subject to both standards like any doc — a skill
covers one procedure, stays within the always-loaded size ceilings, and is
discoverable through the harness's skill list.

A skill is also an **instruction an agent must follow** — its body is a
prompt. The doc half (context efficiency, discoverability) is this skill;
the instruction half (what wording an agent reliably acts on) is
`skill://prompt-craft`. They do not duplicate each other: this one shapes
the document, that one shapes the instruction — a shared rule is linked in
one place, never restated in the other.

## Before writing, answer these questions

- Who is this for? (developer running the server, agent implementing a
  feature, contributor adding enrichment)
- What single question does it answer?
- What information does this audience NOT need?

If a piece of information belongs to a different audience or topic, put it
there instead. Cross-reference by linking, never by copying.

## Signs you're violating context efficiency

- A doc has two distinct audiences (e.g., "this section is for
  contributors, that section is for administrators")
- A doc covers two unrelated topics
- You're tempted to copy-paste content from another doc
- A reader has to skip large sections to find what they need
- Content is duplicated or concepts are explained twice

## How to update documentation

1. Identify the audience for your content
2. Find the existing doc for that audience and topic
3. If no doc exists, create one with a clear single purpose
4. Add your content to the right place
5. Update cross-references in other docs
6. Check that you haven't duplicated information that belongs elsewhere
7. Make sure that humans and agents will find your document if they start
   by reading AGENTS.md.

## When the standard changes

The standards are the source. If a rule you need does not exist yet, propose
it as a standards change (with user agreement) — a per-doc patch that fights
the standard is a finding.

## Where a rule the review bot must enforce lives

A rule the review bot must enforce lives in the project documentation the
bot reads — the `repo_context_files` list in `.pr_agent.toml` — never in
`extra_instructions`. `extra_instructions` holds only meta-instructions
(how to run the compliance check); a substantive rule appended there is
hidden from users and agents, bypasses the doc structure, and drifts
unnoticed. To add an enforceable rule:

1. Write it as a real standard/doc with a sensible name, in a sensible
   place (`standards/` for code-repo standards, `docs/` for repo docs),
   discoverable from AGENTS.md.
2. Ensure that doc is in the review bot's `repo_context_files` (for code
   repos: the scaffold copies `standards/` into `docs/` and lists them).
3. The bot then reads and enforces it — no `extra_instructions` change.
