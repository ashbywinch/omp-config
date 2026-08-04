---
name: write-documentation
description: |
  Documentation standards and conventions — the required doc set and folder
  structure (docs/PRD.md or docs/PRD/, docs/TECHSPEC.md, docs/PLAN.md with
  mandated content), AGENTS.md as bootloader with every doc discoverable
  from it, context efficiency, density, no-duplication, one topic per file,
  and the documentation-quality checklist.
---

When asked to write or update documentation, follow these principles.

## AGENTS.md is a bootloader, not an operating system

AGENTS.md loads everything else and gets out of the way. It holds the quick
start, the decision tree that routes every task to the right doc, and the
rules that apply to **every** agent in the repo — nothing more. Content that
only some agents need (a subsystem's internals, a rare workflow, a surface
standard) belongs in the doc the tree links to, never in AGENTS.md itself.
Test: is this genuinely relevant to 100% of agents working in this repo? If
not, it does not belong in the bootloader.

**Every doc must be discoverable from AGENTS.md** — directly or by following
links (one level deep is the norm). A doc that AGENTS.md cannot lead to is
undiscoverable, and undiscoverable documentation is a finding: it does not
exist for the reader who starts where all readers start.

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

## Single Source of Truth — Never Duplicate

Each piece of information lives in exactly one place. Other docs link to it. They don't repeat it. A duplicated fact is a finding: the two copies drift, and the reader cannot tell which is current. When you are tempted to copy content into a second doc, link instead — the link is the duplication-free way to reuse.

**Good:** The development guide says "See the column reference for details" and links to column-reference.md.

**Bad:** The development guide repeats the column layout inline — two copies, one of which will go stale.

## One Topic Per File — the Docs' Separation of Concerns

One reason to change per doc file, exactly as one reason to change per module
(docs/coding-standards.md 'Separation of concerns'): each doc covers one
topic for one audience. A doc with two audiences or two unrelated topics is a
finding — split it and link. If you need to cover a subtopic for a different
audience, create a separate file and link to it. The question before writing
or editing: "what single question does this doc answer?" — a second question
means a second file.

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

## The Required Doc Set

Every project's `docs/` folder carries three documents, and the review bot
checks PRs against them (they are listed in `.pr_agent.toml`
`repo_context_files`). Each of the three is **itself held to the quality
rules of this skill** — the Documentation Checklist and the density rules
below; a PRD, TECHSPEC, or PLAN that fails context efficiency is a finding,
not a formatting preference. They follow those rules like any other doc.

### Requirements — `docs/PRD.md` (or `docs/PRD/` with subsections when big)

The product requirements document. Sections, in order:
- **JTBD first** — a comprehensive set of very high-level Jobs To Be Done,
  the opening section. May include emotional JTBD ("feel the family is
  remembered"), not only functional ones.
- **Personas** — a small group, specific enough to drive decisions. A
  persona is decision-useful when two plausible product choices differ
  under it; a persona that cannot change a decision is filler.
- **Constraints that shape everything**: cost to run, longevity of the
  system, backups, monitoring and tracing once in production, access and
  auth, likely scale at different phases (data size, number of users, …),
  and hosting limitations — internal or external — stated explicitly when
  either is off the table.
- Big PRDs split into subsections (`docs/PRD/`) instead of one wall; each
  subsection keeps the density rules.

### Technical spec — `docs/TECHSPEC.md` (or `docs/TECHSPEC/` with subsections when big)

How it will all be done:

- **Technology choices**, with the alternatives considered and why they
  lost.
- **Spikes required to confirm** — named, with what each must prove before
  the choice is locked.
- **Strategic technical decisions** that follow from requirements —
  reference the requirement by name and content, not only by number
  (numbers change).
- **Architecture layers as a mermaid diagram** — plus anything else
  important about the architecture: data flows, physical architecture.
  Multiple diagrams are fine, one per concern.

### Plan — `docs/PLAN.md` (or `docs/PLAN/` with subsections when big)

The intended phases:

- Each phase states its **inputs, outputs, operations, and the quality
  gates of the app after that phase**. The inputs and outputs are the
  **software's** at that phase, not the project phase's: inputs are what the
  app consumes (data, users, artifacts it reads), outputs are what the app
  produces (capabilities, results, artifacts it writes) — never the phase's
  project-management artifacts ("docs written", "code landed"). The quality
  gate is the app behaving correctly at that point, not a project deliverable
  being "done". A phase is complete when the app passes its gates.
- **Phases never depend on outputs of later phases** — every phase ships
  in order.
- **Phases are ordered for earliest user value** — each phase is the
  minimum possible addition that drives real value.

## How to Update Documentation

1. Identify the audience for your content
2. Find the existing doc for that audience and topic
3. If no doc exists, create one with a clear single purpose
4. Add your content to the right place
5. Update cross-references in other docs
6. Check that you haven't duplicated information that belongs elsewhere
7. Make sure that humans and agents will find your document if they start by reading AGENTS.md.
