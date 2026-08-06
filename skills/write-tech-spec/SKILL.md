---
name: write-tech-spec
description: Write a TECHSPEC that locks the design before code — technology choices with evaluated alternatives, a component breakdown, a layer or pipeline model, and an object model that is the naming authority for the implementation. Use when a PRD is ready to implement, or when a design must be pinned down before coding.
---

# Write Tech Spec

One output: `docs/TECHSPEC.md` (or `docs/TECHSPEC/` when big), held to
`docs/documentation-structure.md` and the documentation-quality checklist.
A TECHSPEC is complete when a new contributor can name the classes before
any code exists.

## The four mandated sections

The review bot checks TECHSPEC against `docs/documentation-structure.md`;
all four below are required, in order after the architecture diagram.

1. **Technology choices.** Alternatives table: every meaningful option
   considered, evaluated against the PRD's constraints (cost, longevity,
   scale, hosting), and why each loser lost. Mark choices locked vs gated on
   a named spike. A single option is a habit, not a decision — a choice
   with no loser was never evaluated.
2. **Component breakdown.** Every component/module: its responsibility, its
   interfaces (what it provides and consumes), and the data it owns.
   Components are the code's boundaries before the code exists.
3. **Layer or pipeline model.** Layers exist in almost every design; if you
   cannot name them, the design is not finished. State the one-way
   dependency rules between layers and encode them in an architecture test
   at scaffold time — absolute globs from the repo root, never `./`-relative
   (a relative glob matches nothing and the test passes vacuously; see
   `skill://archunitpython-glob-rules`). Pipeline stages are named for their
   domain function, never for the mechanism.
4. **Object model.** The domain nouns, each with purpose, key fields, and
   relationships. Derive them from the PRD's JTBD and the domain expert's
   vocabulary — the words users actually use. Analytical objects (findings,
   metrics, runs, intervals) are objects too. **This is the naming authority
   for the code.**

## Process

1. Read the PRD; extract the constraints — they drive the tech choices.
2. List the domain nouns: what the users and the JTBD talk about. Nouns
   become objects; verbs become operations on objects. When a verb has no
   object, the object is the thing the verb operates on: a builder builds a
   *graph*, a classifier assigns a *phase* — the graph and the phase are the
   nouns, never the builder or the classifier.
3. Design the object model first — it is the heart of the spec. An object
   earns its place by being what the domain has, not what the pipeline does.
4. Then components, then layers, then tech choices. Iterate freely, but the
   object model must end explicit.
5. **Name the code from the object model.** A class or module whose name is
   not an object-model noun is a finding: either the model is missing an
   object or the name is wrong. Fix one, never keep both out of sync.
6. **Design analyses and experiments around the primary object, not the
   intermediate that produces it.** When the domain object is an interval
   (a phase run, a span, a session), measure intervals — per-event evidence
   is how you derive them, not what you report. A feasibility spike measures
   the object, not the pipeline step that builds it.

## Naming checks — run before writing any name

- Is it a noun from the object model? If it is a verb, a mechanism noun
  (Builder, Manager, Classifier, Fetcher), or a layer name (core, util,
  common), find the domain noun instead.
- If the model has no noun for it, extend the model first — then name.
- Docs may carry process vocabulary ("the classify step of the pipeline");
  code may not.

## Checklist

- [ ] Alternatives table: losers named with reasons; locked vs spike-gated
- [ ] Every component: responsibility, interfaces, owned data
- [ ] Layer/pipeline diagram + one-way rules; arch test planned (absolute globs)
- [ ] Object model: every domain noun with purpose, key fields, relationships
- [ ] Code names are object-model nouns (spot-check: no Builder/Manager/Classifier)
- [ ] Analyses target the primary object, not intermediate evidence
