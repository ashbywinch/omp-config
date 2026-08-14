---
name: business-org-model
description: |
  The business and personal org model behind the Notion tree — who owns
  what, how products and value streams are parented. Consult before routing
  insights or creating epics/VS.
---

# Business Org Model

The org model behind the Notion tree (see `skill://notion-database-management` for mechanics, `skill://epic-quality-standard` for the top-level-page validation rule). Two worlds: **the business** and **the CEO's personal life**.

## The Business (CEO)

```
The Business (CEO)
├── Strategy & Business Development      ← CEO's strategy shop
│   ├── Business Model & Idea Validation
│   ├── Strategic Planning and Roadmapping
│   ├── New Service Offerings Development
│   ├── Patent Licensing & MVP Development
│   └── strategy epics (Business Development, Market Analysis, Innovation Concept, Strategic Foundation, Strategy Execution)
├── Product & Engineering (CTO)         ← owns Product P&L for ALL products; product GMs report here
│   ├── AI Platform Development         ← the AI Platform product (GM-owned)
│   │   ├── AI Platform Marketing      ← per-product, under the GM
│   │   ├── AI Platform Sales
│   │   └── AI Platform Customer Success
│   ├── Loft Product P&L (GM: Loft)    ← product P&L, not revenue
│   │   ├── Family-Agnostic Product (VS) ← the productized Loft (was Epic 9)
│   │   └── Marketing (the Loft's)     ← per-product, under the GM
│   ├── Operating Model as Code & AI Agent Core   ← engineering enablement
│   │   └── Meta-Process for Document Creation
│   ├── AI Agent Design Principles & Core Functionality
│   └── Technology Excellence           ← engineering enablement (renamed from Developer Experience, 2026-08-12)
│       ├── Maintainability            ← renamed from the Standards VS
│       │   ├── Epic 3.1.1: Standards Tooling & Distribution
│       │   ├── Epic 3.1.2: Best-Practice Delta & Hoisting
│       │   ├── Epic 3.1.3: Dev Machine Setup (complete)
│       │   ├── Epic 3.1.4: Repo & Toolchain Hygiene
│       │   ├── Epic 3.1.5: Code Quality Tooling & Refactoring
│       │   ├── Epic 3.1.6: Review Bot & Enforcement
│       │   └── Epic 3.1.7: Code Review Tooling
│       ├── Agent Autonomy
│       │   ├── Epic 3.2.1: Chat Workflow & Agent Improvement
│       │   ├── Epic 3.2.2: Custom Harness
│       │   ├── Epic 3.2.3: Process & Skill Development
│       │   ├── Epic 3.2.4: Tooling & Cost Efficiency (complete)
│       │   └── Epic 3.2.5: Agent-owned CI
│       ├── Reliability in Production
│       │   └── Epic 3.3.1: Deployment & Rollouts
│       ├── Process Improvement
│       │   └── Epic 3.4.1: Standards Re-Review
│       └── Cost & Value of the Dev Process
│           ├── Epic 3.5.1: Dev-Process Cost Tracking
│           └── Epic 3.5.2: Cost-to-Value Improvement
├── Marketing (CMO)                    ← enablement / standards ONLY
│   ├── Go-to-Market Strategy
│   └── User & Market Discovery
├── Sales & Customer Success (CRO)     ← enablement + the revenue function
│   ├── Partnership Strategy & Integration
│   └── Revenue                        ← hosts future product revenue streams
├── Operations & Quality (COO)
│   ├── Continuous Improvement & Quality Management
│   │   └── Business Process Excellence
│   └── Operating Model Validation
├── Legal, Risk & Compliance (CLO)     ← direct to CEO
└── People & Organization (CHRO)       ← direct to CEO
```

**Technology Excellence** is enablement only: it produces standards, tooling, and process — it does not do the work in the repos. Repo-implementation work (mise migration, zero baselines, standards copies) lives under each app's own value stream as a `<App> Standards & Toolchain Compliance` epic.

## Numbering

Epics are numbered within their value stream (3.1.x under Maintainability, 3.2.x under Agent Autonomy, …). The number is the epic's home; the tree is the source of truth. Legacy numbers from the pre-2026-08-12 tree (3.3.x, 3.4.x as children of Epics 3.3/3.4) are retired.

## GM model (how products are owned)

- A **GM owns a product's P&L** (cash basis — contribution/P&L, not revenue). The GM's value stream hosts the whole product: per-product marketing, sales, CS, engineering.
- **GMs report to the CTO**, who owns Product P&L across all products. Revenue (the CRO's function) is separate from product P&L.
- **Enablement orgs** (CMO, CRO, COO, CTO's platform arms) provide support and standards only — GMs may draw on them, but per-product work lives under the GM, never under the enablement function.
- Per-product value streams are named for the product and parented under the product GM's value stream — NOT under the shared Marketing/Sales/CS functions.
- **What counts as a business product**: anything intended to generate revenue — including a version of a personal product packaged for sale (e.g. a family-history app's family-agnostic edition). A product used only for personal goals is a personal product, not a business product; the same underlying product can exist on both sides as two value streams (personal use vs revenue edition).

## Personal value streams (the CEO's life goals)

Top-level, KPI-able, life-goal value streams. **Each app has its own dedicated development value stream** — never hijack the life-goal VS as if the app were the only thing fulfilling it:

- **Connection to Roots** — family history, heritage, heirlooms. Hosts **Loft App Development** (the personal Loft; was Epic 6, converted 2026-08-12) and Accessibility (voice input).
- **Personal Effectiveness** — the PA (PA Development & Implementation, PA Engagement Plans) and **Chat-Workflow App Development**.
- **Quality of Life** — Health (→ Manage Long Covid → **Health Tracking App Development**, was Epic 4.1), House Accessibility (→ Epic 2 House Move, **Houses App Development**, was Epic 2.4), Enjoy Food and Cooking (→ **Freezer & Meal App Development**, was Epic 4.2).
- **Lifelong Learning** — **Side-by-Side App Development** (was Epic 7.1.1), **News App Development** (was Epics 7.2.1 + 7.2.2), **Learning Notes App Development** (was Epic 7.3), Learning Russian, Personal News & Trends, Books-to-Anki App Development, Feed-Generator App Development.
- **Energy-Envelope App Development** — under Quality of Life.

Every app value stream hosts its `<App> Standards & Toolchain Compliance` epic (mise migration, zero-baseline elimination, standards copy + pin, python version pin, chat-workflow adoption, deployment where applicable).

## Routing rules

- The **product** a note touches decides its home: business product → under that product's GM (Product & Engineering); personal product → under the matching personal VS.
- **Per-product marketing/sales/CS notes** go under the product GM's value stream, never the enablement org — but only **indirectly**: they land under an epic inside that value stream. A task or epic is never parented directly to a value stream in the routing step; the value stream is the territory, the epic is the container.
- **Enablement/standards notes** (process, quality, standards, compliance) go under the C-suite function — for engineering standards/tooling, under Technology Excellence's Maintainability; enforcement machinery under Agent Autonomy; deployment under Reliability in Production; review cadence under Process Improvement.
- **Per-repo implementation work** goes under the repo's own app value stream (a `<App> Standards & Toolchain Compliance` epic) — never in the enablement tree.
- **Agent-behavior principles** (how the AI should behave, collaborate, take initiative) → AI Agent Design Principles & Core Functionality, or Operating Model as Code for runnable process/playbook work.
- Strategy notes → Strategy & Business Development.
- Nothing is parentless: if no existing VS fits and the work is ongoing (no done point), propose a new VS with a KPI-able name under the right parent; if it's finishable, propose an epic under the right parent.
