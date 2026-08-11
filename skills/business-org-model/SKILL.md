---
name: business-org-model
description: |
  The business and personal org model behind the Notion tree — who owns
  what, how products and value streams are parented. Consult before routing
  insights or creating epics/VS.
---

# Business Org Model

The org model behind the Notion tree (see `skill://notion-database-management` for mechanics, `skill://epic-quality-standard` for validation). Two worlds: **the business** and **the CEO's personal life**. Top-level pages are value streams only — a life goal or a C-suite responsibility. No product, epic, or mid-level function is ever top-level.

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
│   │   ├── Epic 9: Family-Agnostic Product
│   │   └── Marketing (the Loft's)     ← per-product, under the GM
│   ├── Operating Model as Code & AI Agent Core   ← engineering enablement
│   │   └── Meta-Process for Document Creation
│   ├── AI Agent Design Principles & Core Functionality
│   └── Developer Experience           ← engineering enablement
│       └── Standards
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

## GM model (how products are owned)

- A **GM owns a product's P&L** (cash basis — contribution/P&L, not revenue). The GM's value stream hosts the whole product: per-product marketing, sales, CS, engineering.
- **GMs report to the CTO**, who owns Product P&L across all products. Revenue (the CRO's function) is separate from product P&L.
- **Enablement orgs** (CMO, CRO, COO, CTO's platform arms) provide support and standards only — GMs may draw on them, but per-product work lives under the GM, never under the enablement function.
- Per-product value streams are named for the product and parented under the product GM's value stream — NOT under the shared Marketing/Sales/CS functions.

## Personal value streams (the CEO's life goals)

Top-level, KPI-able, life-goal value streams:
- **Connection to Roots** — family history, heritage, heirlooms. Hosts the personal Loft (Epic 6) and Accessibility (voice input).
- **Personal Effectiveness** — the PA (PA Development & Implementation, PA Engagement Plans).
- **Quality of Life** — Health (→ Manage Long Covid → Epic 4.1), House Accessibility (→ Epic 2 House Move, Epic 2.4 Houses App), Enjoy Food and Cooking (→ Epic 4.2).
- **Lifelong Learning** — Learning Russian, Personal News & Trends.

## Routing rules

- The **product** a note touches decides its home: business product → under that product's GM (Product & Engineering); personal product → under the matching personal VS.
- **Per-product marketing/sales/CS notes** go under the product GM's value stream, never the enablement org.
- **Enablement/standards notes** (process, quality, standards, compliance) go under the C-suite function.
- **Agent-behavior principles** (how the AI should behave, collaborate, take initiative) → AI Agent Design Principles & Core Functionality, or Operating Model as Code for runnable process/playbook work.
- Strategy notes → Strategy & Business Development.
- Nothing is parentless: if no existing VS fits and the work is ongoing (no done point), propose a new VS with a KPI-able name under the right parent; if it's finishable, propose an epic under the right parent.
