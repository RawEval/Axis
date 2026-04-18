# Axis — The proactive workspace layer for teams

**RawEval Inc · Bengaluru · 2026**

---

## The problem

The average Series A–C team runs on 8–12 SaaS tools at once. Decisions made in Slack never land in Notion. Tickets in Linear drift out of sync with client emails. The PRD in Drive contradicts the thread from three weeks ago. **Nobody knows.** The cognitive cost of managing this fragmentation is enormous — and entirely invisible until someone misses a follow-up or ships the wrong version.

Existing "AI with connectors" products require you to ask. But the hardest part of this job isn't answering questions — it's **knowing what to ask in the first place**. By the time you ask, the contract has been waiting three days.

## What Axis is

Axis is the workspace layer that runs in the background across your connected tools — Slack, Notion, Gmail, Google Drive, GitHub, Linear — and **surfaces what you'd miss before you ask**.

- **Proactive.** Watches your stack continuously. Flags unanswered DMs, stale docs, contradictions, missed follow-ups, undocumented decisions.
- **Safe.** Every write shows a diff preview and is rollback-able for 30 days. Sends are always confirmed.
- **Compliant.** Bring your own OAuth credentials. Your tokens, your audit log, your compliance review.
- **Team-native.** Organizations with role-based delegation — owners invite admins, admins invite managers, managers invite members. Every grant is scoped and audited. Roles describe permissions, never job titles.
- **Yours.** Model-agnostic (Claude today, swappable). Your data never trains anyone's model without opt-in.

## Why now

Cross-tool OAuth + LLM reasoning quality crossed the "actually reliable" threshold in 2025. Then Anthropic shipped Claude Connectors in January 2026 — **validating the category** but leaving the important parts unbuilt. The proactive layer, the enterprise RBAC, the write-back safety rails, the BYO credentials — none of that is in claude.ai, and won't be, because Anthropic is a model lab, not a workspace infrastructure company.

## The wedge

| | Anthropic's Claude | Axis |
|---|---|---|
| Connects to your tools | ✅ (9 apps) | ✅ (Notion, Linear, GitHub, Gmail, Slack, Drive) |
| **Proactive background monitoring** | ❌ | ✅ |
| **Writes with diff + rollback** | ❌ | ✅ |
| **Bring your own OAuth** | ❌ | ✅ |
| **Org-native RBAC** | ❌ | ✅ |
| **Team-level activity stream** | ❌ | ✅ |
| **Model flexibility** | Anthropic only | Any |

Axis is not a better chat. Axis is a **different product shape** — infrastructure Anthropic won't build.

## Who it's for

- **Anyone who lives in 8+ SaaS tools and spends half the day synthesizing what happened across them.** Morning brief + proactive surfaces so you stop missing follow-ups.
- **Anyone who shares tools with a team and needs to delegate scoped access without giving away the keys.** Role-based invites; read-only members; writes always gated.
- **Anyone building internal AI tooling who doesn't want to maintain an eval + correction loop themselves.** We run it.
- **Anyone in an environment where the compliance team says "we can't put our tokens in a third-party vendor's OAuth app."** Bring your own OAuth client; Axis stores encrypted tokens but connects through *your* registered integration.

We do not target a specific job title — Axis is built around *what you do with your tools*, not *what your business card says*.

## How it works — one user flow

> Sarah runs ops at a Series A startup. It's 8:00 AM.
>
> Axis's morning brief on her phone says:
> *"Yesterday: 3 Slack DMs you haven't replied to. The Acme renewal doc hasn't been updated in 11 days but you discussed it in #product Tuesday. A decision about the pricing tier was made in Slack with no Linear ticket. Your 2pm with Acme has no prep doc."*
>
> Sarah taps the Acme line. Axis drafts a prep doc pulling from the last 3 weeks of Acme-related Slack threads, emails, and Notion pages. Shows her the diff. Sarah hits Confirm. The doc lands in the right Notion folder; a link is posted to #acme-engagement.
>
> Sarah also invites her teammate Priya to Axis with the **member** role, scoped to the Acme project only. Priya can run reads, cannot connect new tools, cannot run writes without approval. Priya's first query works immediately.
>
> Total time: 3 minutes. Without Axis: half a day, and the prep doc wouldn't exist.

## The team model — delegation by scoped role, not by title

This is what separates Axis from every other AI tool:

```
               ┌──────────────┐
               │  Organization │
               │  Acme Team   │
               └──────┬───────┘
                      │
            ┌─────────┴─────────┐
            │                   │
         ┌──┴──┐             ┌──┴──┐
         │Owner│             │Admin│
         └──┬──┘             └──┬──┘
            │                   │
            │         ┌─────────┴─────────┐
            │         │                   │
            │      ┌──┴────┐         ┌────┴───┐
            │      │Manager│         │Manager │
            │      └──┬────┘         └────┬───┘
            │         │                   │
            │      ┌──┴──┐             ┌──┴──┐
            │      │Member│             │Viewer│
            │      └─────┘             └─────┘
            │
            └── can grant/revoke any role below
```

Every edge is an invite. Every node is a member with a scoped role. The roles are **owner / admin / manager / member / viewer** — five permission tiers, deliberately **without reference to job titles**. A role describes what a person can do inside Axis, never what they are in their company. Someone can be an Owner in the "Internal Ops" org and a Viewer in the "Client Alpha" org on the same day, without the product making a single assumption about hierarchy, seniority, or title.

In-app, the Members page renders this as a visual graph showing who invited whom and who has access to which projects — not a title-laden table. Every grant is scoped (which project? which connectors?) and every change is in the audit log.

Anthropic has none of this.

## Metrics we care about

| Metric | 3 months | 6 months | 12 months |
|---|---|---|---|
| Paying users | 10 (beta) | 100 | 500 |
| ARR | ₹0 | ₹30 Lakh | ₹1.5 Crore |
| WAAU (weekly actions/user) | 5+ | 8+ | 12+ |
| Proactive accept rate | N/A | 25%+ | 40%+ |
| Connectors per active user | 3+ | 5+ | 7+ |

## Pricing

| Plan | Price | For |
|---|---|---|
| **Free** | ₹0 | Solo, 1 project, 3 connectors, 50 actions/mo, no proactive |
| **Pro** | ₹2,999/mo | Solo power user. Unlimited projects, proactive layer, BYO OAuth |
| **Team** | ₹9,999/mo (flat, ≤10 seats) | Small teams. Org with RBAC, shared projects, per-member activity |
| **Enterprise** | Custom | SSO, on-prem/hybrid, SLA, DPA, custom roles |

## The ask

Pre-seed round — raising ₹2.5 Cr to ship Phase 1 (3 months) and reach 100 paying users. 10 beta users on day one from the RawEval network. First hires: full-stack lead engineer + frontend engineer + product designer. Current state: founding team + 20-page spec + scaffolded codebase + 18 DB tables + 8 microservices + working Notion OAuth flow + professional workbench UI.

## Why us

RawEval has shipped AI evaluation infrastructure at scale. We understand the operational cost of running per-user background workers and correction loops — because we already run them. Axis is the productized version of the workspace we built internally. Every design decision traces to a real ops pain we lived.

## What we've shipped to date (2026-04)

- 18-table Postgres schema with full spec-compliant data model
- 8 microservices (FastAPI + LangGraph + Node) with structured logging, correlation IDs, health probes
- End-to-end auth + JWT + bcrypt + lockout
- Real Anthropic LangGraph planner with prompt caching
- Real Notion OAuth flow with BYO credentials support
- Projects as first-class workspace containers
- 10 architecture ADRs and 80+ pages of internal docs
- Professional web UI (Tableau-inspired) with 10 routes
- iOS + Android skeletons with shared KMM business logic layer

**Status:** pre-seed ready. Ship the proactive layer + RBAC in Phase 1, reach 100 paying users in Phase 2, expand to 500 + Team tier in Phase 3.

---

**Contact:** raghav@raweval.com
**Demo:** axis.raweval.com/request-demo (Phase 2)
**Spec:** full 20-page product + engineering spec available under NDA
