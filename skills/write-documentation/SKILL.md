---
name: write-documentation
description: |
  Principles and conventions for writing maintainable, context-efficient
  documentation for human and agent readers.
---

When asked to write or update documentation, follow these principles.

## Context Efficiency Principle

Every documentation file must only contain information that is relevant to its topic and audience. For each document, be clear about exactly what the (single) topic and intended audience is.

**Before writing a doc, answer these questions:**
- Who is this for? (developer running the server, agent implementing a feature, contributor adding enrichment)
- What single question does it answer?
- What information does this audience NOT need?

If a piece of information belongs to a different audience or topic, put it there instead. Don't cross-reference by copying content. Cross-reference by linking.

All documentation must be usable by humans or by AI agents. Both must be able to navigate the documentation to find what they need, starting from the entry point of AGENTS.md.

### Signs You're Violating Context Efficiency

- A doc has two distinct audiences (e.g., "this section is for contributors, that section is for administrators")
- A doc covers two unrelated topics
- You're tempted to copy-paste content from another doc
- A reader has to skip large sections to find what they need
- Content is duplicated or concepts are explained twice

## Single Source of Truth

Each piece of information lives in exactly one place. Other docs link to it. They don't repeat it.

**Good:** The development guide says "See the column reference for details" and links to column-reference.md.

**Bad:** The development guide repeats the column layout inline.

## One Topic Per File

Each doc file covers one topic for one audience. If you need to cover a subtopic for a different audience, create a separate file and link to it.

## Avoid Redundancy

Before adding content to a doc, check if it already exists elsewhere. If it does, link to it instead of repeating it. If it doesn't, put it in the most logical place and link from other docs.

## Delete, Don't Archive

Obsolete content is a liability. When something is no longer accurate, delete it. Don't rename it "legacy", don't add a deprecation notice. If it's wrong, remove it.

## Docs Must Match the Code

When you rename a function, module, or tab, update the docs in the same commit. When you add a feature, document it before moving on. Outdated docs are noise.

## API Keys Never Go in Docs

API keys, passwords, and secrets never appear in documentation or `.env` files. They live in the shell environment only.

## Documentation Checklist

Use this to evaluate whether a doc follows Context Efficiency:

- [ ] Single, clearly stated audience
- [ ] Single, clearly stated topic
- [ ] No content that belongs to a different doc
- [ ] No duplicated content from other docs (link instead)
- [ ] Every section is relevant to the stated audience
- [ ] Title and first paragraph make the purpose clear
- [ ] Links to related docs where readers might need them

## Density & Concision

Docs are read inside a limited AI context window. Every sentence costs
context. Write for density: the smallest set of words that preserves every
fact and decision.

### Rules as explicit negatives

State constraints as prohibitions, not preferences. "Never X" reads
faster and is followed more reliably than "be careful about X".

```markdown
# Low-density (vague preference)
Avoid swallowing errors silently when catching exceptions.

# High-density (explicit rule)
**Never swallow errors.** Every `except` block must log, re-raise, or
handle observably. Bare `except: pass` is forbidden.
```

### Commands over prose

Prefer executable commands to descriptive sentences. `make test` beats
"run the test suite to verify everything works".

```markdown
# Low-density
To start the development environment, use the make run command.

# High-density
make run    # backend :8080 + frontend :5173, auto-reload
```

### Tables over prose

A rule per row beats a paragraph per rule. Use a table when a fact has
consistent fields (state, meaning; layer, rule, files; fake, default).

### Canonical code examples over exhaustive enumeration

One right/wrong code pair teaches more than a list of edge cases. Mark
them ✗/✓ or Wrong/Right. Never enumerate every failure mode — show the
pattern.

### One-line contracts

A contract that fits one line is easier to hold in context:
`compute()` MUST return an `Attempt`. Prefer that over three sentences
of explanation.

### Decision-relevant context only

Keep only background that changes a decision. Cut filler ("Every node's
value is…"), motivation the reader already has, and restated rules.

### Size ceilings

Always-loaded files (AGENTS.md, CLAUDE.md, skill bodies) target ~150–200
lines / <32 KiB — loaded in full every session, so bloat is paid every
session. Referenced docs (pulled in only when relevant) can be longer,
but still densify prose first; density matters less for them than for
always-loaded files.

### Link, don't paste

A fact lives in exactly one place; other docs link to it. References one
level deep — a doc points to another doc, not through a chain.

### Section structure for tasks

When a doc describes how to do something, use the task-card shape: goal
(one verb), scope (exact paths), constraints (must / never), acceptance
(verifiable command).

### Density checklist

- [ ] Every sentence carries a fact, a decision, or a constraint
- [ ] Rules are explicit negatives ("Never X"), not vague preferences
- [ ] Commands replace descriptions where executable
- [ ] Tables replace paragraphs where fields are consistent
- [ ] Code shows a canonical ✗/✓ pair, not exhaustive cases
- [ ] No filler, no restated motivation
- [ ] Always-loaded files within the ~150–200 line ceiling

## How to Update Documentation

1. Identify the audience for your content
2. Find the existing doc for that audience and topic
3. If no doc exists, create one with a clear single purpose
4. Add your content to the right place
5. Update cross-references in other docs
6. Check that you haven't duplicated information that belongs elsewhere
7. Make sure that humans and agents will find your document if they start by reading AGENTS.md.
