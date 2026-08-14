---
name: business-org-model
description: |
  The business and personal org model behind the Notion tree — who owns
  what, how products and value streams are parented. Consult before routing
  insights or creating epics/VS.
---

# Business Org Model

The org model behind the Notion tree (see `skill://notion-database-management` for mechanics, `skill://epic-quality-standard` for the top-level-page validation rule). Two worlds: **the business** and **the CEO's personal life**.

**The live tree lives in the Notion Epics and Value Streams databases — this skill holds the rules, not the tree.** Query Notion for current parentage before routing or creating; the rules here decide *where* things belong.

## The Business (CEO)

The business side's value streams and their parentage live in Notion — query before routing. The rules below decide where things belong.

**Engineering enablement is enablement only**: it produces standards, tooling, and process — it does not do the work in the repos. Repo-implementation work lives under each app's own value stream as a `<App> Standards & Toolchain Compliance` epic.

## GM model (how products are owned)

- A **GM owns a product's P&L** (cash basis — contribution/P&L, not revenue). The GM's value stream hosts the whole product: per-product marketing, sales, CS, engineering.
- **GMs report to the CTO**, who owns Product P&L across all products. Revenue (the CRO's function) is separate from product P&L.
- **Enablement orgs** (CMO, CRO, COO, CTO's platform arms) provide support and standards only — GMs may draw on them, but per-product work lives under the GM, never under the enablement function.
- Per-product value streams are named for the product and parented under the product GM's value stream — NOT under the shared Marketing/Sales/CS functions.
- **What counts as a business product**: anything intended to generate revenue — including a version of a personal product packaged for sale (e.g. a family-history app's family-agnostic edition). A product used only for personal goals is a personal product, not a business product; the same underlying product can exist on both sides as two value streams (personal use vs revenue edition).

## Numbering

**A dotted number is a path.** `3.4.1` names a child of `3.4`, which names a child of `3` — anything numbered `3.4.1` must sit under a `3.4` under the `3` family (the engineering-enablement root). Numbered value streams carry their number in the name; an epic's dotted number must match its parent chain, rename when parentage changes, and an unnumbered page makes no path claim.

## Personal value streams (the CEO's life goals)

Top-level, KPI-able, life-goal value streams. **Each app has its own dedicated development value stream** — never hijack a life-goal VS as if the app were the only thing fulfilling it. App development value streams sit under the matching life-goal VS (the current mapping is in Notion — query before routing), each hosting its `<App> Standards & Toolchain Compliance` epic.

## Routing rules

- The **product** a note touches decides its home: business product → under that product's GM (Product & Engineering); personal product → under the matching personal VS.
- **Per-product marketing/sales/CS notes** go under the product GM's value stream, never the enablement org — but only **indirectly**: they land under an epic inside that value stream. A task or epic is never parented directly to a value stream in the routing step; the value stream is the territory, the epic is the container.
- **Enablement/standards notes** (process, quality, standards, compliance) go under the C-suite function — for engineering standards/tooling, under the engineering-enablement standards & tooling stream; enforcement machinery under its agent-autonomy stream; deployment under its reliability stream; review cadence under its process-improvement stream; dev-process cost and value notes under its cost & value stream. Resolve current stream names from Notion.
- **Per-repo implementation work** goes under the repo's own app value stream (a `<App> Standards & Toolchain Compliance` epic) — never in the enablement tree.
- **Agent-behavior principles** (how the AI should behave, collaborate, take initiative) → AI Agent Design Principles & Core Functionality, or Operating Model as Code for runnable process/playbook work.
- Strategy notes → Strategy & Business Development.
- Nothing is parentless: if no existing VS fits and the work is ongoing (no done point), propose a new VS with a KPI-able name under the right parent; if it's finishable, propose an epic under the right parent.
