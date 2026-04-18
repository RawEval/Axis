# Workbench-style UI redesign for Axis

**Date:** 2026-04-18
**Status:** Design — awaiting user approval
**Owners:** UI/UX redesign initiative
**Related:** ADR 006 (amendment), CLAUDE.md invariant #1 (amendment), upcoming "Workbench-of-Axis" companion app

## Problem

The current Axis web UI feels like an operator dashboard: navy 52-px icon-only sidebar, single blue accent, vivid per-tool brand colors on `/connections`, an amber-pulsing 4-button-plus-Deny permission modal, and admin-dense pages (`/memory`, `/credentials`, `/settings`) that read like Tableau panels. The user's verdict: *"Nothing is good. Nothing is user-friendly."*

The reference is RawEval's Workbench app: dark-first, single signal-orange accent, Instrument Serif display + DM Mono chrome, hairline borders, no shadows at rest, two-button confirmations, status communicated through small mono uppercase pills. The user describes it as *"a math problem — basic, optimistic, trusting, usable by a 60-year-old"*.

A new "Workbench-of-Axis" companion app is also planned. The token system designed here must serve both Axis and that companion without divergence.

## Goals

1. Make the Axis web UI feel like Workbench — same tokens, typography, spacing, component patterns.
2. Ship light **and** dark themes from day one, with a system toggle that respects `prefers-color-scheme` on first load.
3. Replace the 4-option permission grid with a single Allow + Deny prompt.
4. Move write actions to optimistic-with-undo, except for irreversible writes (Gmail send, GitHub merge, deletes, audience > 3).
5. Remove all per-tool brand coloring on `/connections`.
6. Keep every architectural invariant that isn't explicitly amended (data isolation, eval-on-every-action, OAuth encryption, role labels stay `owner/admin/manager/member/viewer`).

## Non-goals

- Mobile (`apps/mobile-ios`, `apps/mobile-android`) is out of scope for this round. They will adopt the same tokens later via `packages/kmm-shared` and a parallel SwiftUI port — tracked separately.
- No new pages, no new features, no new routes. This is a pure aesthetic + interaction redesign of existing surfaces.
- No backend changes beyond what's required to support the two amendments.

## Amendments

### A1 — ADR 006: collapse the lifetime grid

ADR 006 currently prescribes four user-visible lifetime choices per grant (`once / project / 24h / forever`) plus a separate Deny button. The DB schema (lifetime column with values `session / 24h / project / forever`) is preserved unchanged.

**New surface:** a single Cancel + Allow modal. "Allow" defaults to `lifetime = project`. The text below the action describes what's about to happen in plain English ("Axis will read your Notion docs in *Marketing Q2* until you turn it off"). A small ghost link "Change scope…" opens a one-line popover with three radio options (`just this run / this project / forever`) — discoverable, not in your face. Deny stays a peer button to Allow.

**New surface for irreversible actions:** the same modal, but the Allow button text is the action itself ("Send email", "Merge PR", "Delete file") and the modal cannot remember the answer — `lifetime` is forced to `task`. ADR 006's "always gate, every time" capabilities (Gmail send, GitHub merge) keep that behavior.

**Per-capability scope panel:** new section on `/settings` called "What Axis can do" — a flat list of every granted capability with its current scope and a Revoke button. This is where power users tune lifetimes after the fact. No grid in the heat of the moment.

ADR 006 doc gets a "2026-04-18 amendment" section at the bottom describing this.

### A2 — CLAUDE.md invariant #1: optimistic writes with 30s undo

Current invariant: *"Every write action requires user confirmation. Non-negotiable in Phase 1."*

New invariant: *"Every write action is either (a) optimistic-with-undo for ≥30 seconds, or (b) hard-gated with a confirm modal. Reversible writes default to (a); irreversible writes default to (b). The user can flip the default per capability in /settings."*

Reversible (default optimistic): Slack post-as-me, Notion append, GitHub comment, Drive comment, Linear status change.
Irreversible (default hard-gate): Gmail send, GitHub merge, any delete, any send to audience > 3, any edit on a doc shared outside the user's org.

UI surface: a slim toast slides in from the bottom-right, 200 ms, with mono text ("Sent to **#growth** · Undo (30s)") and an undo button that calls a `POST /v1/actions/{id}/undo` endpoint. After 30 s the toast fades; undo is gone. The toast itself is part of the design system (see Components below).

CLAUDE.md gets an amendment block under "Core architectural invariants" pointing to this spec.

## Tokens

Token names match Workbench so the design system can be lifted from the monorepo verbatim. Color values are quoted by CSS custom property name. Where Axis needs a light counterpart, both are listed.

### Color (dark theme — primary)

| Token | Value | Use |
|---|---|---|
| `--color-bg` | `#0A0A0B` | Page background |
| `--color-bg-surface` | `#141415` | Cards, sidebar, modal panels |
| `--color-bg-muted` | `#1C1C1E` | Inputs, hovered rows |
| `--color-bg-elevated` | `#232326` | Hovered cards, popovers |
| `--color-text-primary` | `#FAFAFA` | Body text, headings |
| `--color-text-secondary` | `#A1A1AA` | Subtitles, descriptions |
| `--color-text-muted` | `#71717A` | Inactive nav, timestamps |
| `--color-text-faint` | `#52525B` | Placeholders, dividers' labels |
| `--color-border` | `#27272A` | Hairline borders everywhere |
| `--color-border-strong` | `#3F3F46` | Hovered borders, focus rings |
| `--color-border-subtle` | `#1E1E21` | Sub-borders inside cards |
| `--color-signal` | `#FF6B35` | Single accent — primary CTA, focus, active nav |
| `--color-signal-hover` | `#FF8A5C` | Primary hover |
| `--color-signal-subtle` | `rgba(255,107,53,0.12)` | Focus ring fill, active nav bg |
| `--color-success` | `#22C55E` | Success state |
| `--color-warning` | `#EAB308` | Warning state |
| `--color-error` | `#EF4444` | Destructive state, deny button |
| `--color-info` | `#3B82F6` | Info badges |

### Color (light theme — counterpart)

| Token | Value |
|---|---|
| `--color-bg` | `#FAFAFA` |
| `--color-bg-surface` | `#FFFFFF` |
| `--color-bg-muted` | `#F4F4F5` |
| `--color-bg-elevated` | `#E4E4E7` |
| `--color-text-primary` | `#0A0A0B` |
| `--color-text-secondary` | `#52525B` |
| `--color-text-muted` | `#71717A` |
| `--color-text-faint` | `#A1A1AA` |
| `--color-border` | `#E4E4E7` |
| `--color-border-strong` | `#D4D4D8` |
| `--color-border-subtle` | `#F4F4F5` |
| `--color-signal` | `#FF6B35` (unchanged) |
| `--color-signal-hover` | `#E55A2B` |
| `--color-signal-subtle` | `rgba(255,107,53,0.08)` |
| Semantic colors | unchanged |

Theme toggle lives in the user menu (top-right). On first load, respects `prefers-color-scheme`. Choice persists in `localStorage["axis.theme"]` and is mirrored to `document.documentElement[data-theme]`.

### Typography

| Token | Family | Use |
|---|---|---|
| `--font-display` | `'Instrument Serif', Georgia, serif` | Page titles only (`h1`) |
| `--font-body` | `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif` | Everything else |
| `--font-mono` | `'DM Mono', ui-monospace, 'SF Mono', monospace` | Status badges, timestamps, button labels, breadcrumbs, code, diff viewer |

Type scale (px): `12 / 13 / 15 (base) / 17 / 20 / 24 / 32`. Line heights: `1.08 / 1.3 / 1.5 / 1.7`. Letter spacing: `0 / -0.02em / 0.06em (mono UI labels) / 0.12em (uppercase mono)`.

### Spacing, radius, shadow

- Spacing: 4 px base (`--space-1` … `--space-24`).
- Radius: `4 / 8 / 12 / 16 / 9999`. Buttons and cards = `8`. Modals = `12`. Pills = `9999`.
- Shadow: `--shadow-md` only on hover lifts and the toast. **No shadows at rest.** Hairline borders carry all elevation.

## App shell

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar (220px, collapsible to 56px)  │  Topbar (56px)     │
│  Logo                                  ├────────────────────┤
│  ─────                                 │                    │
│  Ask                                   │  Page content       │
│  Activity                              │  max-width 1100px   │
│  History                               │  px 48 / py 32 64   │
│  Tools                                 │                    │
│  Team                                  │                    │
│  ─────                                 │                    │
│  «collapse                             │  (optional toast    │
│                                        │   bottom-right)     │
└────────────────────────────────────────┴────────────────────┘
```

- **Sidebar** is `bg-surface` with right hairline. Items are 18 px lucide-react icon + body-font label, padding `10px 16px`, gap `12px`. Active = `bg-muted` + `font-weight 500` + `text-primary`. Inactive = `text-muted`. Collapse button at the bottom is faint, no chrome.
- **Topbar** is `bg-surface` with bottom hairline, height 56 px. Left: project switcher as a ghost button with mono uppercase project name + small chevron. Right: theme toggle, then user avatar (initial circle, hairline border, no fill). Both open Workbench-style dropdowns (border, no shadow).
- **No status bar**. The footer green/red dot from the current shell is killed; connectivity surfaces only when broken (a top inline banner).

## Pages

For each page: the *only* change unless noted is theme/typography/component swap. Layout structure stays. Deletions and behavioral changes are explicit.

### `/login`, `/signup`
Single centered card, max-width 420 px, hairline border, 48 px padding. Display-font title. One primary button. Email + password inputs are the standard component. No marketing copy, no logos, no gradient hero.

### `/chat` — the main surface
Conversation flow stays top-to-bottom. Changes:
- Live progress card → swap to a hairline-bordered `card-surface` containing the existing `LiveTaskTree`. Step dots use semantic colors at full saturation but only 5 px diameter; pulse stays for `running` and `awaiting_permission`.
- Diff viewer → mono font, `+` lines `bg = success @ 8% / text = success`, `−` lines `bg = error @ 8% / text = error / strikethrough`, prefix in faint mono.
- Cited response → text spans get a 1 px hairline underline in `--color-signal`, plus a tiny mono superscript number that links to the source. Sources list below the response is a series of hairline-bordered rows, mono provider label + body-font title + secondary excerpt + faint timestamp.
- Sticky command bar → single rounded-md input, `bg-muted`, signal focus ring (2 px `--color-signal-subtle`), Send is a ghost-styled icon button on the right that turns primary on input.

### `/feed` — Activity
- "Needs your attention" → vertical list of hairline-bordered rows. Each row: 16 px lucide icon (faint, **same color for all sources** — recognition comes from the mono provider label), bold body title, secondary excerpt, mono timestamp + signal-type pill on the right. Confidence % becomes a mono `LOW · MED · HIGH` token, no percentages shown.
- "Recent activity" → identical row pattern, no section header — separated by a faint divider with a mono `EARLIER TODAY` label.
- Empty state: dashed-border box, 36 px faint icon, body-font message, optional ghost CTA.

### `/history`
Hairline-bordered rows in a single list. Per row: mono timestamp left, body-font prompt centered, mono `DONE` / `FAILED` pill right, ghost "Open" link on hover. No badges, no token counts on the index — those live in detail.

### `/connections`
Same 3-column grid, but each card is the standard `card-surface` (hairline border, no shadow at rest, `hover-lift` adds `shadow-md` and `border-strong`). Inside: 18 px monochrome connector mark in `text-secondary` color, mono uppercase connector name, body-font description, status pill at the bottom (`CONNECTED` / `NOT CONNECTED` / `COMING SOON`). Connect = primary button; Disconnect = ghost. **No tool brand colors anywhere.**

### `/team`
- Header → display-font title, ghost "Invite" button (primary on hover).
- Members → hairline-bordered list, one row per person: 32 px initial circle, body-font name, mono uppercase role pill (`OWNER / ADMIN / MANAGER / MEMBER / VIEWER` — no other titles, ever), faint email. The `MembersGraph` org chart is removed; it added complexity without payoff.
- Pending invites → same row pattern, with a `PENDING` pill and a ghost "Resend / Revoke" link.

### `/memory`
- Overview → three flat stat blocks (no cards), large display-font number, mono uppercase label below. No three-column dl table.
- Search → standard input, filter buttons become a single mono-segmented control (`ALL · PERSON · WORK · CHANNEL`). Results → hairline-bordered rows, no tier/score columns by default; "Show details" ghost link toggles a row expansion that reveals tier, score, type. Power-user information is one click away, not in your face.

### `/credentials`
One section per tool. Each section: hairline-bordered card, mono uppercase tool name + status pill (`USING AXIS DEFAULT` / `USING YOUR APP`), body-font description. Single primary button: "Use your own credentials" → opens the form inline within the same card (no modal). Form is the standard input/label pattern. Help link is a ghost "Read the guide ↗" line at the bottom.

### `/settings`
Three sections, each a hairline-bordered card:
- **Account** — flat key-value rows, no `dl` grid.
- **Theme** — three-way segmented control (`SYSTEM · LIGHT · DARK`).
- **What Axis can do** — *new section per A1.* Flat list of every granted capability with mono capability name + body-font scope label + ghost Revoke button.
- **Output quality** — composite score as a single number with display font, faint trend indicator below. "Recent runs" → 5-row hairline list, no card.
- **Sign out** is a ghost danger link at the bottom. Not a button.

## Component patterns

| Component | Spec |
|---|---|
| **Button — primary** | `bg-signal`, `text` `#FFFFFF`, padding `10px 20px`, radius `8`, mono uppercase label `12px`, letter-spacing `0.06em`, hover `bg-signal-hover` |
| **Button — secondary** | transparent bg, `border 1px solid border`, `text-primary`, hover `bg-elevated` + `border-strong` |
| **Button — ghost** | transparent, no border, `text-secondary`, hover `text-primary` + `bg-elevated` |
| **Button — danger** | `bg-error`, white text, used only for destructive confirms |
| **Input** | `bg-muted` (dark) / `bg-surface` (light), `border 1px solid border`, padding `10px 14px`, focus = `border-signal-border` + `box-shadow 0 0 0 2px signal-subtle` |
| **Card** | `bg-surface`, `border 1px solid border`, radius `12`, padding `20`, **no shadow at rest**, `hover-lift` adds `translateY(-2px)` + `shadow-md` |
| **Status badge** | mono `11px`, uppercase, letter-spacing `0.08em`, padding `2px 8px`, radius `9999`, bg = semantic @ 8 %, border = semantic @ 18 %, color = semantic, optional 5 px pulse dot |
| **Toast** | bottom-right, slide-in 200 ms, padding `12px 16px`, bg = semantic @ 10 %, border = semantic @ 20 %, mono label + body action, auto-dismiss 4 s (Undo toast = 30 s) |
| **Modal** | backdrop `rgba(0,0,0,0.6)` + `backdrop-filter: blur(4px)`, max-width 420 px, `bg-surface`, `border 1px solid border`, radius `12`, padding `24`, two-button footer (secondary + primary), Esc dismisses |
| **List row** | hairline divider above, padding `16px 20px`, hover `bg-muted` |
| **Segmented control** | mono uppercase labels, hairline border around the group, divider between segments, active segment `bg-muted` + `text-primary`, others `text-muted` |

## What's deleted

- Custom shadows `sm-strong`, `panel`, `popover` from `tailwind.config.ts`.
- All hardcoded source brand colors in `SOURCE_COLORS`.
- The `MembersGraph` component (`components/team/`).
- All-caps section headers like "NEEDS YOUR ATTENTION" — replaced by the `EARLIER TODAY`-style mono dividers.
- The 4-option permission modal (`components/chat/permission-modal.tsx`) is rewritten, not deleted — same file, single-confirm pattern.
- The 6-px-tall green/red status bar at the bottom of the shell.
- Symbol-character icons in the nav (⌘◉↻⚡◎) — replaced with lucide-react.

## Workbench-of-Axis (forward compatibility)

The user has flagged a separate "Workbench app for Axis" coming. This redesign keeps that easy:

- All tokens are CSS custom properties on `:root` and `[data-theme]`. The companion app imports the same `globals.css`.
- Component primitives go into `packages/design-system` so both apps consume the same React components.
- No tokens or components are named with `axis-` prefixes — they're generic (`button-primary`, `card-surface`, etc.) so the companion can adopt them without renames.

## Implementation surface (rough)

Files that change (concrete implementation order is the next planning step, not this spec):

- `apps/web/tailwind.config.ts` — new token mapping
- `apps/web/app/globals.css` — CSS custom properties for both themes, font imports
- `apps/web/components/shell/*` — sidebar, topbar, theme toggle, no status bar
- `apps/web/components/ui/*` — every primitive
- `apps/web/components/chat/permission-modal.tsx` — single Allow + Deny
- `apps/web/components/diff-viewer.tsx` — mono + opacity-tinted lines
- `apps/web/components/team/members-graph.tsx` — deleted
- `apps/web/app/(app)/*/page.tsx` — every page swapped to new components
- `apps/web/app/(auth)/*/page.tsx` — login/signup card
- `packages/design-system/*` — promoted primitives, exported for the companion
- `docs/architecture/permissions-model.md` — A1 amendment block
- `CLAUDE.md` — A2 amendment block under invariant #1
- New: `apps/web/components/ui/toast.tsx` — undo-capable
- New: `apps/web/app/(app)/settings/capabilities/` (or settings tab) — capability scope panel

## Risks

- **The optimistic-undo path needs backend support.** Every write capability needs an `undo` handler. If a capability cannot undo (e.g. external email already delivered), it must be in the irreversible list. The capability registry needs an `undoable: bool` field; A1's per-capability scope panel uses it to choose the right modal.
- **Light theme on a Workbench-derived palette is less battle-tested.** Workbench is dark-first. The light-theme tokens above are derived, not lifted; the first build will need contrast verification.
- **Instrument Serif at small sizes is tricky.** Restrict it to `h1` only (page titles). Everything else stays sans/mono.
- **Replacing the permission modal touches an ADR.** ADR 006 must be amended in the same PR as the UI change, or the docs and code drift.

## Open questions for review

None — the user delegated open decisions ("do whatever you feel is most good for the startup") on 2026-04-18. If anything in this spec doesn't match what they had in mind, this is the moment to flag it.
