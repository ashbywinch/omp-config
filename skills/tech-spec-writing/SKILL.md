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
- **Flow specs** (CONTRIBUTIONS, IMPORT-PRD) — a specific flow's
  end-to-end rules: invariants, seams, review gates. The TECH-SPEC points
  at them; it does not restate them.
- **Conventions docs** (UI, CHAT-UX, coding-standards) — visual and
  interaction conventions; the normative rules.
- **Working logs** (a fixes plan, a decisions log) — never normative;
  they record the loop's findings and statuses.
- **Session records** (interviews/) — what happened and when; append-only.

There is no separate "UX requirements" category: presentation requirements
live in the PRD, presentation conventions in the conventions docs.

## Stack defaults (the converged house choices)

A TECH-SPEC starts from the defaults; it departs from them only with a
recorded reason.

- **Python web servers: FastAPI + uvicorn.** The framework owns request
  parsing — query decoding, cookies, JSON bodies, redirects. A
  hand-rolled HTTP server reimplements each wrong one at a time (the
  auth bug class: a percent-encoded query param handed to Google, a
  `session=`-prefixed cookie header, a JSON body). If the app has any
  HTTP surface beyond static-file serving, that surface is FastAPI. The
  spec's test section then exercises the real HTTP stack (uvicorn on an
  ephemeral port, or the framework's test client) so the framework's
  decode/cookie/redirect behavior is covered — unit tests of the flow
  logic miss it.
- **Python toolchain**: uv, ruff, basedpyright, pytest (see the scaffold
  language layers).
- **The object model** — name the nouns: the aggregate (the archive /
  the store / the collection), the interchange format, the server, the
  derived projection. Verbs are methods on the nouns; nothing is named
  after a verb, a transport medium, or out-of-domain jargon. When the UI
  has a word for a concept, the code uses the same word.
- **Identity and auth**: Google sign-in via the authorization-code web
  flow (skill://google-auth). A LAN app registers a hostname that
  resolves to its IP (sslip.io) as the redirect URI — never a raw IP,
  never the device flow as a browser path. The identity lives in the
  app's own data (people records carry emails), never in code or config.

## What the spec must record

- **The data model**: the primary content vs the derived projection
  (derived is computed from primary, never hand-edited, regenerable); the
  store's write rules (append-only supersede, tombstones); the validation
  seams (a write seam that refuses what the model rejects).
- **The machine's rules as the spec** — not the intent, the rules: the
  derived computations (what is calculated, never stored), the render
  rules (one render per page, what each surface shows), the fail-loud
  points (write-seam parsing, gates that refuse the build). If an eval or
  a test encodes the rule, the spec states the rule and the eval enforces
  it.
- **The deployment shapes**: dev (LAN, phone access — hostname callback,
  private data), production (domain, TLS). The private-data boundary (the
  archive's data is gated behind the session; the app shell stays public
  so the gate can load).
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
