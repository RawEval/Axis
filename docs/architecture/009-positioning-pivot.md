# ADR 009 — Positioning pivot

**Date:** 2026-04-16
**Status:** Accepted
**Supersedes:** `axis_full_spec.docx` §01 "Executive Summary" one-liner
**Trigger:** competitive analysis — Anthropic shipped OAuth Connectors (Jan 2026), Skills, Plugins, and Cowork tasks inside claude.ai. The "connect every tool to one agent" category now has a model-lab incumbent with a structural cost advantage.

## TL;DR

**Old pitch:** *"One app. Connect everything. Just tell it what to do."*
**New pitch:** *"The proactive workspace layer for teams. Axis watches your Slack, Notion, Gmail, GitHub, and Linear in the background and catches what you'd otherwise miss. Writes require a diff and 30-day rollback. Bring your own OAuth. Built around how your team actually delegates access."*

The category we are competing in is **not** "chat with your tools." That fight is lost — Anthropic owns the consumer chat surface and ships connectors natively. The category we are competing in is **"the workspace intelligence layer that runs in the background, surfaces what matters, and delegates safely down an org chart."** Anthropic will not build this because:

1. It is infrastructure, not a chat feature. Different product shape.
2. It requires per-tenant background workers, relevance-engine tuning, and a correction loop — all of which are operationally expensive for a horizontal model lab to run per-user.
3. It requires enterprise-grade RBAC + BYO credentials. Anthropic's consumer auth model is not set up for this.
4. It requires a team/org data model. claude.ai is organized around conversations, not organizations.

## What changed in the market

From Anthropic's Jan–Mar 2026 releases (see `axis_full_spec.docx` §15 risk #1 for the forecast this validates):

- **Interactive Claude Apps / Connectors** — OAuth 2.0 to 9 apps (Slack, Canva, Figma, Box, Clay, Asana, Amplitude, Hex, Monday). Renders live UI inside claude.ai.
- **Claude Skills** — packaged instructions/workflows/files loaded on demand by Claude.
- **Plugins** — bundles of skills + connectors + slash commands as one installable unit.
- **Cowork** — recurring and scheduled tasks.
- **Usage policy update (Feb 2026)** — consumer-account OAuth tokens cannot be used outside claude.ai / Claude Code.

The original Axis one-liner covered a category Anthropic now ships. That's fine — the spec (§15) explicitly forecast this risk and said *"speed is the only answer."* Speed is not enough; **positional differentiation** is the real answer.

## The four things we do that Anthropic won't

### 1. Proactive background monitoring

Anthropic's connectors are reactive — you have to ask. Axis runs per-user background workers that ingest events from every connected tool, score them through the relevance engine (spec §6.3, `activity-feed.md`), and **surface what matters before the user asks**:

- "You have 3 Slack DMs from yesterday you haven't replied to"
- "The roadmap doc got 4 new comments but you haven't looked"
- "The Acme contract thread hasn't moved in 48h"
- "A decision was discussed in #product but there's no Linear ticket"

This is a different product shape from a chat-with-connectors app. It runs 24/7, per user, producing `activity_events` rows and surfacing high-signal ones.

**Why Anthropic won't build this:** horizontal model labs do not run per-customer background workers. It's not their operational model.

### 2. Write-back with diff preview + 30-day rollback

Anthropic's connectors lean on live interactive UIs. Their writes are not diffed and not rollback-able.

Axis treats writes as first-class, gated, and reversible (spec §6.5):
- Every write action shows a `DiffViewer` preview before execution
- Confirmed writes are logged with a pre-write snapshot
- **Rollback available for 30 days** on Notion pages, Google Docs, GitHub commits, Linear tickets
- Sends (Gmail, Slack, GitHub merge) are *always* gated regardless of trust level

**Why Anthropic won't build this:** reversibility is operationally expensive (snapshot storage, versioning infra) and the consumer product doesn't need it. Enterprises do.

### 3. Bring-your-own OAuth credentials

Anthropic's connectors use Anthropic's OAuth apps — in a provider's audit log, the access shows as `Anthropic`.

Axis supports two modes (ADR 003 `byo-credentials.md`):
- **Default** — user clicks "Connect Notion", uses Axis's app, done in 10 seconds
- **BYO** — user pastes their own `client_id` / `client_secret` in Settings → Credentials. Access shows in Notion's audit log as *their* internal integration, not Axis.

**Why Anthropic won't build this:** their entire business model is centralized. Per-user OAuth apps are anti-centralized.

### 4. Org-first data model

Anthropic organizes around conversations. Axis organizes around **organizations** with **role-based delegation** (ADR 010 `org-and-rbac.md`):

- **Organization** — the team or company
- **Member roles** — owner / admin / manager / member / viewer. These are permission tiers, not job titles. A role says what a member *can do*, never what they *are*.
- **Projects** — belong to the org, have their own member list
- **Delegation** — an owner invites admins; admins invite managers; managers invite members; every grant is scoped and audited. The chain is deliberately generic: we do not hard-code any assumption about how a team labels its seats.

This models how real teams actually work: scoped delegation of access to people, without presuming what titles those people hold. Anthropic's consumer product has no concept of this.

**Why Anthropic won't build this:** they have Anthropic Enterprise tier, but RBAC + delegation inside a product experience is Linear/Notion/GitHub territory, not Anthropic's core.

## Revised positioning pyramid

| Layer | Old | New |
|---|---|---|
| **One-liner** | "One app. Connect everything." | "The proactive workspace layer for teams." |
| **Hero noun** | "agent platform" | "workspace layer" |
| **Hero verb** | "connects" | "watches + surfaces" |
| **Primary differentiator** | Cross-tool chat | Proactive monitoring nobody else does |
| **Second differentiator** | Tool-agnostic neutrality | Write-back safety + rollback |
| **Third differentiator** | Eval + correction loop | Org-native RBAC + BYO OAuth |
| **Target persona** | Ops lead | Anyone who shares tools with a team they delegate to |
| **Anti-pattern** | "A smarter Claude" | Being compared to Claude at all |

## Revised moat ranking

From spec §16, ranked by durability **in light of competitive reality**:

1. **Proactive monitoring data + relevance tuning per user.** Accumulated signals tune each user's cold-start assumptions. Anthropic cannot replicate this because they don't run per-user workers.
2. **Write-back infrastructure (snapshots, diffs, rollback).** Operationally expensive. Table-stakes for compliance users; nice-to-have only for consumers.
3. **Org-native RBAC data model.** Structural. You can't bolt this onto a conversation-first product.
4. **Correction loop + fine-tune dataset** (spec §6.6). Still the compounding-data moat from the original spec, but less unique now that Anthropic ships feedback loops in claude.ai. Still valuable for enterprise-specific behavior.
5. **Model-agnostic architecture.** Axis can swap to Llama / OpenAI / Gemini / fine-tuned Mistral at the orchestrator. Anthropic locks to Anthropic. Important for enterprises that don't want single-vendor risk.
6. **BYO OAuth.** Compliance wedge. Can't-bolt-on retrofit for a centralized product.

## What we stop saying

- "The single agent for every tool." — Anthropic says this now.
- "Just tell it what to do." — Anthropic says this now.
- "We'll beat Anthropic on X." — We will not pick that fight.
- "Cross-ecosystem intelligence." — Anthropic has this for 9 apps and growing.

## What we start saying

- "The workspace layer that runs in the background."
- "Watches your Slack, Notion, Gmail, GitHub, Linear so you don't miss things."
- "Writes show you the diff first. Rollback for 30 days."
- "Bring your own OAuth. Your credentials, your audit log."
- "Scoped roles that match how your team actually delegates."
- "Your data never trains anyone's model without your opt-in."

## Impact on the codebase

Structural changes triggered by this pivot (see individual tasks for each):

- **ADR 010** — new org + RBAC data model
- **Migration 007** — `organizations`, `organization_members`, `organization_invites`, add `org_id` to `projects` + `project_members`
- **api-gateway `/orgs` routes** — CRUD + invite flow
- **Web UI** — org switcher (replaces the "single user with projects" mental model), Members page, Invite modal
- **Mobile apps** — same 4-tab model, same API client contract, designed to match web

Features that become **higher priority** because of this pivot:
- The proactive layer (spec §6.3) — **this is now the hero feature**, not a Phase 2 nice-to-have
- The write-back engine (spec §6.5) — **this is now the second hero feature**
- RBAC / delegation (new ADR 010)

Features that become **lower priority**:
- Multi-model routing (was a "neat" thing, now just a compliance bullet)
- Voice/desktop/widgets (spec §8.2) — Anthropic's Claude Desktop exists; not our fight

## Impact on pricing / plans

Not in scope for this ADR, but noted for Phase 2 product work:

- **Free** — 1 user, 1 project, 3 connectors, 50 actions/month, no proactive layer. Anthropic's connectors are free on Pro; we need to be cheaper or meaningfully better at this tier.
- **Pro** — 1 user, unlimited projects, proactive layer ON, eval dashboard, BYO OAuth allowed. ₹2,999/mo.
- **Team** — org with ≤10 members, RBAC, shared projects, per-member activity stream. ₹9,999/mo flat.
- **Enterprise** — unlimited members, SSO, data residency, DPA, SLA, on-prem/hybrid option. Custom.

Team tier is new. It's the wedge this positioning unlocks — Anthropic doesn't have a Team SKU with org-level RBAC.

## References

- `axis_full_spec.docx` §15 (original risks — this ADR addresses risk #1 "foundation model labs ship this directly")
- `axis_full_spec.docx` §16 (original moat — this ADR re-ranks them)
- [Anthropic Release Notes — April 2026](https://releasebot.io/updates/anthropic)
- [Claude AI Connectors: One-Click Tool Integrations (2026)](https://max-productive.ai/blog/claude-ai-connectors-guide-2025/)
- `docs/architecture/activity-feed.md` — the proactive layer schema
- `docs/architecture/byo-credentials.md` — the BYO OAuth pattern
- `docs/architecture/org-and-rbac.md` (ADR 010) — the new org + RBAC model
- `docs/pitch/one-pager.md` — the pitch doc derived from this ADR
