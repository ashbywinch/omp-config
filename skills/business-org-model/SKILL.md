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

- **Strategy & Business Development** — the CEO's strategy shop (value prop, roadmapping, new offerings, patents, strategy epics).
- **Product & Engineering (CTO)** — owns Product P&L for ALL products; product GMs report here. Engineering enablement lives here: **Technology Excellence** (renamed from Developer Experience, 2026-08-12) with five child value streams — **Maintainability**, **Agent Autonomy**, **Reliability in Production**, **Process Improvement**, **Cost & Value of the Dev Process** — plus Operating Model as Code & AI Agent Core, and AI Agent Design Principles & Core Functionality.
- **Marketing (CMO)** — enablement/standards only (Go-to-Market Strategy, User & Market Discovery).
- **Sales & Customer Success (CRO)** — enablement + the revenue function (Partnership Strategy, Revenue).
- **Operations & Quality (COO)** — Continuous Improvement & Quality Management, Operating Model Validation.
- **Legal, Risk & Compliance (CLO)** and **People & Organization (CHRO)** — direct to CEO.

**Technology Excellence is enablement only**: it produces standards, tooling, and process — it does not do the work in the repos. Repo-implementation work lives under each app's own value stream as a `<App> Standards & Toolchain Compliance` epic.

## GM model (how products are owned)

- A **GM owns a product's P&L** (cash basis — contribution/P&L, not revenue). The GM's value stream hosts the whole product: per-product marketing, sales, CS, engineering.
- **GMs report to the CTO**, who owns Product P&L across all products. Revenue (the CRO's function) is separate from product P&L.
- **Enablement orgs** (CMO, CRO, COO, CTO's platform arms) provide support and standards only — GMs may draw on them, but per-product work lives under the GM, never under the enablement function.
- Per-product value streams are named for the product and parented under the product GM's value stream — NOT under the shared Marketing/Sales/CS functions.
- **What counts as a business product**: anything intended to generate revenue — including a version of a personal product packaged for sale (e.g. a family-history app's family-agnostic edition). A product used only for personal goals is a personal product, not a business product; the same underlying product can exist on both sides as two value streams (personal use vs revenue edition).

## Numbering

Epics are numbered within their value stream (3.1.x under Maintainability, 3.2.x under Agent Autonomy, …). **The number is a home, not a path** — an epic numbered 3.4.1 under Process Improvement is not under any epic 3.4; the parent value stream in Notion is the source of truth.

## Personal value streams (the CEO's life goals)

Top-level, KPI-able, life-goal value streams. **Each app has its own dedicated development value stream** — never hijack a life-goal VS as if the app were the only thing fulfilling it. App development value streams (Loft, Houses, Side-by-Side, News, Health Tracking, Freezer & Meal, Learning Notes, Books-to-Anki, Energy-Envelope, Feed-Generator, Chat-Workflow) sit under the matching life-goal VS, each hosting its `<App> Standards & Toolchain Compliance` epic. The current mapping is in Notion.

## Routing rules

- The **product** a note touches decides its home: business product → under that product's GM (Product & Engineering); personal product → under the matching personal VS.
- **Per-product marketing/sales/CS notes** go under the product GM's value stream, never the enablement org — but only **indirectly**: they land under an epic inside that value stream. A task or epic is never parented directly to a value stream in the routing step; the value stream is the territory, the epic is the container.
- **Enablement/standards notes** (process, quality, standards, compliance) go under the C-suite function — for engineering standards/tooling, under Technology Excellence's Maintainability; enforcement machinery under Agent Autonomy; deployment under Reliability in Production; review cadence under Process Improvement; dev-process cost and value notes under Cost & Value of the Dev Process.
- **Per-repo implementation work** goes under the repo's own app value stream (a `<App> Standards & Toolchain Compliance` epic) — never in the enablement tree.
- **Agent-behavior principles** (how the AI should behave, collaborate, take initiative) → AI Agent Design Principles & Core Functionality, or Operating Model as Code for runnable process/playbook work.
- Strategy notes → Strategy & Business Development.
- Nothing is parentless: if no existing VS fits and the work is ongoing (no done point), propose a new VS with a KPI-able name under the right parent; if it's finishable, propose an epic under the right parent.
