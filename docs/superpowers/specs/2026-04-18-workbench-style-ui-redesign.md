# Axis UI redesign — opinionated end-to-end

**Date:** 2026-04-18
**Status:** Design — awaiting user approval
**Canonical source:** [`docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md`](../../compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md) ("the artifact")

This file is a **thin translator**. The artifact is the design — read it first. This file does three things only:
1. Confirms the artifact's prescriptions are adopted wholesale.
2. Maps every prescription onto specific files and packages in this monorepo so the implementation plan that follows can cite real paths.
3. Flags every place the artifact contradicts existing `CLAUDE.md` invariants, ADRs, or scaffolded code, and prescribes the amendment in the artifact's own terms.

Rule when this spec and the artifact disagree: **artifact wins**.

## What we're shipping (one paragraph)

A completely re-skinned and re-modeled Axis web app: zinc-tinted dark-first palette with **ink-cobalt `#3340E6` / `#4F5AF0`** as the single accent, **Söhne (or Inter Display + Inter fallback) + Berkeley Mono (or Commit Mono fallback)** type stack with mono used selectively (~15 % of text, never in headings or body), a **three-column shell** (LeftNav 240 → 56 px · Main · contextual RightPanel 360 px), an **operations-center Home** that replaces the empty-chat first impression, **structured artifacts** (live task tree, diff-first preview cards, citation chips, agent-state dots) instead of chat bubbles, **breathing idle** animation on active runs in place of spinners, and a permission + write interaction model rebuilt around three risk tiers and per-connector trust. Light theme is a faithful mirror, not an afterthought. The whole thing ships behind two feature flags (`VISUAL_V2`, `INTERACTION_V2`) with a 30-day "Use classic Axis" escape hatch.

## Adopted from the artifact (not re-litigated here)

These are decisions taken from the artifact verbatim. If you want detail, jump to the cited section.

| Decision | Artifact section |
|---|---|
| Color tokens (canvas/surface/elevated/sunken/borders/text/accent/semantic) | §2a |
| Agent-state color tokens (`agent.thinking/running/awaiting/recovered/blocked/background`) | §2a |
| Type stack — Söhne primary, Inter fallback; Berkeley Mono primary, Commit Mono fallback; **no Instrument Serif, no Geist** | §2b |
| Type scale (Display/Heading/Body/Caption/Mono) | §2b |
| Spacing 4 px base, radius scale 0/4/6/8/12/16/full, elevation by luminance on dark + shadows on light | §2c |
| Motion durations (micro/short/medium/long/ambient/shimmer), spring + ease-out + linear easings, **breathing idle** keyframe, **shimmer not pulse** for skeletons, `prefers-reduced-motion` collapses to instant | §2c |
| Iconography — Lucide library, sizes 14/16/20/24, plus ~12 commissioned custom marks (5 connector + 5 agent-state + Axis hairline-tick) | §2d |
| Optional sound + haptic vocabulary, defaulted off in enterprise | §2e |
| App shell — LeftNav 240/56, Topbar 48, contextual RightPanel 360, no status bar, no breadcrumbs | §3a |
| **Home = operations center** (Running now / Needs your approval / Connector dots / Recent runs) — not a chat box | §3a |
| Per-page layouts for Login, Chat, Activity, History, Connections, Credentials, Memory, Settings, Team, Projects, Admin | §3b–§3l |
| Component primitives + Axis-native components (LiveTaskTree, DiffViewer, PermissionCard, WritePreviewCard, CitationChip, AgentStateDot, ConnectorTile, MemoryRow) | §4 |
| Agent prompt+run interaction (live tree, citations, error mid-run, cancel) | §5a |
| Permission model A1 (recommendation) | §5b |
| Write model A2 (recommendation) | §5c |
| Correction capture (4 layers) | §5d |
| `⌘P` project switcher, memory inspection, onboarding (demo workspace), multi-tool runs, offline/degraded behavior, full keyboard map | §5e–§5j |
| Empty-state system, error taxonomy, loading states, long/short runs, RTL, color-blind, screen-reader patterns | §6 |
| Phased migration plan with two feature flags and rollback metrics | §8 |

## Codebase translation

The artifact talks in tokens and pages. This is where each lives.

### Tokens & globals

| Artifact concept | File in this repo |
|---|---|
| `bg.*`, `text.*`, `border.*`, `accent.*`, `success/warning/danger/info` | `apps/web/tailwind.config.ts` (extends `colors`) and `apps/web/app/globals.css` (CSS custom properties on `:root` + `[data-theme="light"]`) |
| `agent.*` state tokens | same — namespaced under `colors.agent` |
| Type scale, font families | `apps/web/tailwind.config.ts` (`theme.extend.fontSize`, `fontFamily`) + `apps/web/app/globals.css` (font-face declarations, `font-display` strategy) |
| Spacing, radius, shadow scales | `apps/web/tailwind.config.ts` |
| Motion tokens, `@keyframes breathe`, `@keyframes shimmer`, `prefers-reduced-motion` overrides | `apps/web/app/globals.css` |
| Theme attribute (`data-theme`) + system preference detection | new hook `apps/web/lib/theme.ts`; mounted in `apps/web/app/providers.tsx` |

The current `tailwind.config.ts` palette (`canvas/ink/edge/nav/brand/semantic`) is replaced wholesale. Existing custom shadows (`sm-strong`, `panel`, `popover`) are deleted; new shadow scale ships only on the light theme per artifact §2c.

### Component library

Per artifact §8 Phase 1: primitives are promoted to `packages/design-system` so the upcoming Workbench-of-Axis companion app can consume them without re-implementation. The split:

**Stays in `apps/web/components/ui/`** (composition only, app-specific): nothing — every primitive moves.

**Moves to `packages/design-system/src/components/`** in this order:

1. `Button`, `Input`, `Textarea`, `Select`, `Combobox` (`cmdk`-backed)
2. `Card`, `Badge`, `Toast`, `Modal`, `Popover`, `Tooltip`, `DropdownMenu`, `ContextMenu`
3. `Tabs`, `SegmentedControl`, `ProgressBar`, `SkeletonBlock`
4. `Avatar`, `Kbd`, `EmptyState`, `ErrorState`

**New Axis-native components** (live in `packages/design-system/src/components/axis/` — namespaced because they're domain-loaded):

- `LiveTaskTree` (replaces existing `apps/web/components/chat/live-task-tree.tsx`)
- `DiffViewer` (rewrites existing `apps/web/components/diff-viewer.tsx`)
- `PermissionCard` (replaces existing `apps/web/components/chat/permission-modal.tsx` — note: card, not modal)
- `WritePreviewCard` (new)
- `CitationChip` + `CitationsPanel` (replaces existing `apps/web/components/chat/cited-response.tsx` markup)
- `AgentStateDot` (new — used in LeftNav, Home, task tree, history)
- `ConnectorTile` (new — replaces tool cards on `/connections`)
- `MemoryRow` (new)
- `PromptInput` (new — multi-line auto-resize, slash, @, file drop, voice)
- `BreathingPulse` (animation primitive)

Every component ships with: tokenized styles, ARIA annotations from artifact §6 / accessibility section, Storybook entry, dark+light visual regression test (Playwright + Chromatic), keyboard-behavior unit test.

### Shell & nav

| Artifact piece | File |
|---|---|
| Three-column shell wrapper | `apps/web/components/shell/shell.tsx` (rewritten) |
| LeftNav (240/56 collapse) | `apps/web/components/shell/nav-rail.tsx` (rewritten — keep file path, replace contents) |
| Topbar (48 px, project selector, ⌘K chip, connector dots, user) | `apps/web/components/shell/top-bar.tsx` (rewritten) |
| RightPanel (slides in, contextual) | new `apps/web/components/shell/right-panel.tsx` + a `useRightPanel()` store in `apps/web/lib/store.ts` |
| Status bar | **deleted** — `apps/web/components/shell/status-bar.tsx` removed |
| ⌘K command palette | new `apps/web/components/shell/command-palette.tsx` (cmdk) |
| `?` shortcut overlay | new `apps/web/components/shell/shortcut-overlay.tsx` |

### Pages

Each page is rewritten in place; the route file remains, the JSX is replaced with the layout from the cited artifact section.

| Route | File | Artifact section |
|---|---|---|
| `/` (Home — operations center) | `apps/web/app/(app)/page.tsx` (currently the dashboard) | §3a |
| `/login`, `/signup` | `apps/web/app/(auth)/login/page.tsx`, `…/signup/page.tsx` | §3b |
| `/chat` | `apps/web/app/(app)/chat/page.tsx` | §3c |
| `/feed` (Activity) | `apps/web/app/(app)/feed/page.tsx` | §3d |
| `/history` | `apps/web/app/(app)/history/page.tsx` | §3e |
| `/connections` | `apps/web/app/(app)/connections/page.tsx` | §3f |
| `/credentials` | `apps/web/app/(app)/credentials/page.tsx` (becomes a RightPanel inside `/connections`; route may collapse — TBD in implementation plan) | §3g |
| `/memory` | `apps/web/app/(app)/memory/page.tsx` | §3h |
| `/settings` | `apps/web/app/(app)/settings/page.tsx` (becomes tabbed: Account / Appearance / Capabilities / Output quality / Notifications / Advanced / Sign out) | §3i |
| `/team` | `apps/web/app/(app)/team/page.tsx` | §3j |
| `/projects`, `/projects/new` | `apps/web/app/(app)/projects/page.tsx` (+ new sub-route or modal) | §3k |
| Admin dashboard | new `apps/web/app/(app)/admin/page.tsx` | §3l |

### Backend support required

The artifact's interaction model needs backend that doesn't fully exist yet. Each item below is a separate ticket; the implementation plan must order them.

- **Three-tier capability registry** — every capability declares its tier (`0 read / 1 reversible / 2 irreversible`). `services/agent-orchestration/` capability registry gets a `tier: int` field; the artifact's §5b table is the source of truth for assignments.
- **Undo handlers** — each Tier-1 capability needs a server-side `undo(action_id)` that the toast's button calls via `POST /v1/actions/{id}/undo`. New endpoint in `services/api-gateway/`. Saga compensations for cross-connector cascades per artifact §5c.
- **Audience-counter** — for sends (Slack post, Gmail send), the orchestrator must compute recipient count *before* surfacing the preview card, so audience > 3 escalates to Tier 2 modal.
- **Per-capability trust mode** — new table or column on the existing grants table, settable from the Capabilities settings tab. Read by the orchestrator before deciding card vs. modal.
- **Backgrounded runs** — runs > 120 s offer to background; needs persistent run state and a topbar "Running (n)" surface that survives navigation. Already partially in `agent-orchestration` — needs a frontend live store, no schema change.
- **Demo workspace seed** — synthetic Slack/Notion/Gmail data for first-run onboarding (§5g). New script in `scripts/seed-demo-workspace.py`.
- **OpenTelemetry-compatible JSON trace export** — for History page export. Probably a wrapper over existing run telemetry.

## Amendments to existing invariants

Two existing rules collide with the artifact. Both need amendment notes in the same PR that lands the new UI, or the docs and code drift.

### A1 — ADR 006 (`docs/architecture/permissions-model.md`)

**Currently:** the doc prescribes a 4-axis grant (scope × capability × action × lifetime) with four user-visible lifetime choices (`session / 24h / project / forever`).

**Amendment (per artifact §5b):**

- The DB schema and the four-axis model are **preserved unchanged** — no migration needed.
- The user-facing UI is replaced. The PermissionCard exposes only `Allow` (default), `Just once`, `Change scope…`, `Always allow for this project` checkbox, and Deny. `lifetime = session` is the default for `Allow`. `lifetime = task` is forced when `Just once` is clicked. `lifetime = project` is set when the checkbox is ticked. `lifetime = forever` is reachable only from the Capabilities settings tab.
- A **three-tier risk model** is introduced:
  - Tier 0 (read) — pre-approved at connector install; logged in run timeline; no card.
  - Tier 1 (reversible writes) — PermissionCard inline.
  - Tier 2 (irreversible / blast-radius) — modal with type-to-confirm; "Always allow" is **disabled** at this tier; trust mode is ignored.
- Capability assignments to tiers live in the capability registry per the artifact §5b table.
- Edge cases (rapid-repeat passive offer, batch plan-card, denied-then-asked-again, expired-grant badge, prompt-injection downgrade) per artifact §5b.

The amendment goes at the bottom of `docs/architecture/permissions-model.md` under a `## 2026-04-18 amendment` heading and links to this spec and to the artifact.

### A2 — `CLAUDE.md` invariant #1 (write confirmation)

**Currently:** *"Every write action requires user confirmation. Non-negotiable in Phase 1. Exception: trust-level-high users can auto-confirm low-risk writes (Notion append, GitHub comment). Sends are always gated."*

**Amendment (per artifact §5c):**

> Every write action is presented to the user *before* execution. The presentation depends on capability tier:
>
> - **Tier 0 (read):** no preview, logged silently in the run timeline.
> - **Tier 1 (reversible write):** inline `WritePreviewCard` with `Confirm / Edit / Refine / Cancel`. On confirm, the card transforms to a "Sent" state and an undo toast appears for 10 s (interactive) or 30 s (scheduled). On failure, the card transforms to "Failed — Retry / Edit / Cancel."
> - **Tier 2 (irreversible / blast-radius — including any send to audience > 3):** modal with type-to-confirm and a recipient-list review. Trust mode does not apply.
>
> A user may set, per connector, a trust mode (`Strict / Balanced / Trusted`) that relaxes Tier-1 to "Preview, auto-confirm after 5 s" or "Auto for reversible." Tier 2 is unaffected.
>
> Cross-connector writes use the saga pattern: cheapest-to-undo first; the undo toast labels honestly which steps it can and cannot reverse. A failed undo offers a compensating action (delete from Slack, send retraction, etc.) — never silent.

The block goes under "Core architectural invariants" in `CLAUDE.md`, linking to this spec and the artifact §5c.

### A3 — `apps/web` Home route

**Currently:** the Home route presumably opens a dashboard or chat. Per artifact §3a, Home becomes an operations center that **explicitly rejects the chat-first home**. This is not contradicting any existing rule (no ADR specifies a Home), but it's a meaningful product decision worth noting in the implementation plan and probably in `apps/web/CLAUDE.md` if one exists.

## Tech-stack additions

The artifact assumes a few libraries that the current scaffold may not have. Add to `apps/web/package.json`:

- `cmdk` — Paco Coursey's command-palette primitive, for `⌘K` and `⌘P`.
- `@radix-ui/react-*` — already partly present; ensure `Select`, `Popover`, `Tooltip`, `DropdownMenu`, `ContextMenu`, `Tabs`, `Dialog` are installed.
- `framer-motion` — for spring-based arrivals, layout transitions, breathing keyframe variants.
- `lucide-react` — icon library.
- `@tanstack/react-virtual` — virtualization for long chat scrollback (artifact §6 large-data).

Optional / behind a license decision:

- Söhne webfont files (Klim Type Foundry license — ~$4–10k). Falls back to Inter Display + Inter (free) — see artifact §8 risk #2. Inter is the implementation default; Söhne is a token-only swap when licensed.
- Berkeley Mono (Berkeley Graphics license — restricted for IDE-like use). Falls back to Commit Mono (OFL free). Commit Mono is the implementation default; Berkeley is a token-only swap when legal sign-off lands. See artifact §8 risk #1.

## Feature flags

Per artifact §8 risk #3:

- `VISUAL_V2` — gates tokens, shell, primitives, page layouts. Per-user. Off by default during rollout. Ships first, can land independently of `INTERACTION_V2`.
- `INTERACTION_V2` — gates the new PermissionCard / WritePreviewCard / capability-tier behavior. Off by default. Ships behind its own flag so visual rollout can proceed if interaction work slips.
- Per-user "Use classic Axis" escape hatch in Settings → Appearance, available for 30 days after a user is moved into `VISUAL_V2`.
- Auto-rollback metric gates: revert rate > 15 % in 24 h, accessibility violations in prod, error rate on new components > 2× baseline.

Old code stays in place during Phases 0–2 of the artifact's plan (= weeks 1–4) and is deleted only after 60 days of stable 100 % rollout.

## Migration order

Lifted directly from artifact §8. Phases 0–4, weeks 1–14. The implementation plan that follows this spec will turn each phase's bullets into ordered tickets with file paths, owners, and acceptance criteria.

- Phase 0 (week 1) — tokens.
- Phase 1 (weeks 2–3) — primitives in `packages/design-system`.
- Phase 2 (week 4) — shell + ⌘K + shortcut overlay.
- Phase 3 (weeks 5–10) — pages, in this order: Chat → Home → Permissions+Writes (parallel) → Connections → Memory → History+Activity → Settings+Team → Admin.
- Phase 4 (weeks 11–14) — mobile follow-on (iOS/Android consume the design tokens from `packages/design-system`).

## Risks (in addition to the artifact's §8 risks)

- **The Phase 3 page order conflicts with the live `/chat` page being the only thing currently usable.** During weeks 5–6, Chat will be rebuilt while users (or beta users) might rely on the old surface. Mitigation: the `VISUAL_V2` flag must be per-page-routable, not just per-user, so the new Chat can ship to a slice while old History/Activity/Memory still render.
- **Backend tier registry is on the critical path for INTERACTION_V2.** No tiers means no PermissionCard. The implementation plan must front-load the registry change or risk weeks of frontend work waiting on backend metadata.
- **The artifact's "operations-center Home" assumes there are running runs and pending approvals to display.** For a brand-new user, that surface is empty. The empty state per artifact §6 ("Nothing yet" + "Start a run") is the answer; the implementation plan must verify the empty-state path is not an afterthought.
- **The artifact deletes breadcrumbs.** Some sub-routes (settings tabs, admin sub-pages) currently rely on them implicitly. Each instance needs the back-arrow + parent-label pattern from artifact §4 — listing those sites is a Phase 2 task.
- **`packages/design-system` currently uses the old dark theme tokens** (per the audit, `#0a0a0b` bg, `#7c5cff` accent — unused by web). Those tokens are deleted; the package is reseeded with the artifact's token set.

## Open questions for review

None — all decided 2026-04-18.

- **Sans:** Inter Display + Inter for V1. Söhne is a future token-swap upgrade once budget approves.
- **Mono:** Commit Mono for V1. Berkeley Mono is a future token-swap upgrade after legal sign-off.

The spec is fully decided. Implementation plan can begin.
