---
name: tech-spec-writing
description: |
  Write the TECH-SPEC — the mechanics document that turns a product's
  requirements into the architecture: stack defaults (FastAPI for Python
  web servers), the object model, the data flow, and the decisions that
  must be recorded. Companion to write-documentation and the scaffold
  skills; the PRD holds requirements, the TECH-SPEC holds mechanics.
---

# Writing a Tech Spec

The TECH-SPEC is the mechanics document: how the thing works, what it is
built on, and why. The PRD holds *what* (requirements, including
presentation); the TECH-SPEC holds *how* (architecture, data model,
decisions). It is read by the next maintainer six months out and by the
review bot — so its decisions must be concrete enough to review against.

## The spec taxonomy (where things live)

- **PRD** — requirements, including presentation. User needs, personas,
  screen requirements. Product law.
- **TECH-SPEC** — mechanics: stack, data model, architecture, the
  machine's rules. Everything an implementer needs that isn't a product
  decision.
- **Flow specs** (an import flow, a contribution flow — whatever flows
  the domain has) — a specific flow's
  end-to-end rules: invariants, seams, review gates. The TECH-SPEC points
  at them; it does not restate them.
- **Conventions docs** (UI, CHAT-UX, coding-standards) — visual and
  interaction conventions; the normative rules.
- **Working logs** (a decisions log, a fixes/lessons log) — never
  normative; they record the loop's findings and statuses.
- **Session records** (interviews/) — what happened and when; append-only.

There is no separate "UX requirements" category: presentation requirements
live in the PRD, presentation conventions in the conventions docs.

## Stack defaults (the converged house choices)

A TECH-SPEC starts from the defaults; it departs from them only with a
recorded reason.

- **Python web servers: FastAPI + uvicorn.** The framework owns request
  parsing; the rule, its rationale, and the real-HTTP-stack testing
  requirement live in the Python language layer
  (`skills/scaffold-language-layers/SKILL.md`). The TECH-SPEC records
  the choice — no hand-rolled HTTP — and its test section follows the
  layer's testing rule.
- **Python toolchain**: uv, ruff, basedpyright, pytest (see the scaffold
  language layers).
- **The object model** — name the nouns: the aggregate (the collection
  the domain is really about — an archive, a store, a library, whatever
  it is), the interchange format, the server, the
  derived projection. Verbs are methods on the nouns; nothing is named
  after a verb, a transport medium, or out-of-domain jargon. When the UI
  has a word for a concept, the code uses the same word.
- **Identity and auth**: a recorded decision like any other. When the
  app signs users in with Google, `skills/google-auth/SKILL.md` owns
  the flow and its redirect-URI rules — the TECH-SPEC records the
  choice and links; it never restates the mechanics.

## What the spec must record

- **The data model**: the primary content vs the derived projection
  (derived is computed from primary, never hand-edited, regenerable); the
  store's write rules (append-only supersede, tombstones); the validation
  seams (a write seam that refuses what the model rejects).
- **The machine's rules as the spec** — not the intent, the rules: the
  computations (what is calculated, never stored), the render
  rules (what each surface shows, when it renders), the fail-loud
  points (write-seam parsing, gates that refuse the build). If an eval or
  a test encodes the rule, the spec states the rule and the eval enforces
  it.
- **The deployment shapes**: dev (localhost or LAN — the network and
  auth shape follows the deployment; see the auth skill), production
  (domain, TLS). The private-data boundary (the app's private data is
  gated behind the session; the shell stays public so the gate can
  load).
- **The decisions and their dates** — every departure from a default
  carries the reason and the date; a decision without a stated reason is
  churn. When a review overturns a decision, the spec records the
  reversal with the evidence.

## Materialization

The spec's machine rules land in the repo's `docs/coding-standards.md`
and the conventions docs, so the review bot (which reads only
`repo_context_files`) enforces them — a rule that stays only in the
TECH-SPEC is invisible to review. The TECH-SPEC is the reasoning; the
standards are the enforceables; the flow specs are the per-flow detail.

## Common pitfalls

- **Restating the PRD** — the spec holds mechanics, not requirements; a
  requirement repeated in the spec drifts out of sync with the PRD.
- **A stack that fights the defaults** — a hand-rolled HTTP server, an
  invented framework, a verb-named module. The defaults exist because
  they were converged on; depart with a recorded reason.
- **The rule without a stage** — a rule the spec states but nothing
  enforces is a trap: every normative rule gets a guard (an eval, a
  test, a write-seam check) that fails loudly.
- **Decisions without dates or reasons** — the spec's decisions must be
  traceable; a later maintainer needs to know why, and when.
