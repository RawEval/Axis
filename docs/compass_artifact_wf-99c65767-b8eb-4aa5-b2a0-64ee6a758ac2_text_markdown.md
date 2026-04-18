# Axis, redesigned — an opinionated end-to-end spec

Axis should stop dressing as a Tableau-grade admin dashboard and stop cosplaying as a Braintrust Workbench. It should look and behave like what it actually is: **a cross-system workspace agent that reads and writes in your real tools**. That requires warmth without Claude's cream, rigor without Linear's violet, density without Cursor's IDE chrome, and motion without Lovable's sparkles. The rest of this document is a concrete, decision-by-decision blueprint: a new visual system with exact tokens, every page re-laid-out, every component speced, and — where the brief offered A/B/C/D options — a single recommendation with the edge-cases that justify it.

The five most important calls are up-front:

1. **Primary accent: a deep ink-cobalt `#3340E6`** — not Linear violet, not Claude orange, not dashboard blue. Intelligent, calm, decisive, unclaimed.
2. **Typography: Söhne (or Inter Display + Inter as the free fallback) + Berkeley Mono (or Commit Mono as the free fallback)**. No Instrument Serif. No Geist.
3. **Dark-mode-first with luminance layering, not shadows**, and a warm-but-not-cream light mode that holds up in side-by-side demos.
4. **Permission model (A1): Option B "Allow + Just once + Change scope" presented inside an Option C inline-in-chat card**, gated by a three-tier risk model with type-to-confirm for irreversibles.
5. **Write model (A2): Option B "inline preview + Confirm/Edit/Cancel → undo toast" as default, Option D "trust mode per connector" layered as user preference, irreversibles hard-gated** — and a saga pattern for cross-connector cascades so undo never lies.

---

## 1. Diagnosis

### 1a. What's genuinely wrong with the current Axis UI

The current slate+navy+blue-accent Tableau-inspired admin look fails Axis on four structural grounds, not taste grounds.

**It signals "analytics dashboard," which Axis is not.** Axis is an actor, not a viewer. Tableau chrome (dense chart tiles, sidebar of reports, 12-widget home) frames the user as someone reading output. Axis's job is to *do* things on the user's behalf across five systems. A home screen organized around KPI cards and connector counts misrepresents the product to the user in their first five seconds.

**Blue-on-slate is the least differentiated choice in B2B SaaS.** It reads as Salesforce/Workday/ServiceNow/Glean — the corporate-IT register. Every buyer immediately slots it next to the incumbent procurement-approved tools, which is exactly the framing a high-agency AI product doesn't want.

**Density is wrong for an agentic surface.** Admin dashboards reward eye-scan across parallel tiles. Agent surfaces reward attention on one long-running stream with branches and citations. The information architecture has to invert — one focused surface, not twelve peripheral ones.

**No visible agent state.** The current UI has no vocabulary for "thinking," "awaiting permission," "tool-calling," "recovered from error." These are the most important states in the product and they're treated like HTTP loading spinners.

### 1b. What's also wrong with the Workbench reference when applied to an agent workspace

Braintrust's Workbench aesthetic — dark-first near-black, signal-orange, Instrument Serif + DM Mono, hairline borders, uppercase mono status pills, no shadows — is a deliberately internal, data-ops look. It works for eval tooling for exactly the reasons it fails for a workspace agent.

**Instrument Serif is editorial, not agentic.** It signals essay, magazine, "AI with a soul" (the Perplexity/Anthropic register). For an agent that executes tool calls and modifies files, it's tonally wrong — too poetic, too ornamental. The font is also in active backlash in design Twitter (Creative Bloq documented this in Nov 2025). Deploying it in Axis in 2026 is a small gamble on fashion that carries zero product benefit.

**Signal orange alone is austere and, worse, tribal.** It reads as "trace/warning/attention" in eval tooling, which is perfect for a measurement instrument and wrong for a collaborator. Orange is also now culturally tagged to Claude and DALL-E warmth — using it as a primary accent makes Axis read as a Claude derivative.

**Mono-everywhere reads as brutalist and cold.** The moment a workspace product uses DM Mono for status pills, metric chips, *and* body copy, non-technical users (PMs, designers, writers) pattern-match it to "engineering internal tool" and disengage. Mono belongs in Axis, but selectively — tool calls, file paths, shortcut hints, trace output. Never headings or nav.

**"Basic math problem" aesthetic undersells intelligence.** Workbench's restraint is a power move for an eval tool because the data is the spectacle. Axis's spectacle is the agent's reasoning and the work it completes — that needs real visual range: arrival, progress, resolution, confidence, recovery. Hairline borders and no shadows strip too much vocabulary from the palette the product needs.

### 1c. The right visual direction for an AI-native workspace product in 2026

Synthesizing across Linear, Raycast, Arc, Superhuman, Notion AI, Dust.tt, Claude.ai, Replit Agent, Cursor, Warp, Ghostty, v0, Vercel, and Perplexity, five patterns dominate in high-craft 2026 AI surfaces:

1. **Dark-first but with luminance-layered surfaces**, not shadow-layered. Four greys deep (bg → surface → elevated → border) plus zinc-tinted neutrals. Pure black is out; zinc #09090B is in.
2. **One confident accent color, chosen to be non-tribal.** Linear owns #5E6AD2, Claude owns #C15F3C, Raycast owns #FF6363, Supabase owns #3ECF8E, Vercel owns pure monochrome. Anything else is available.
3. **Selective mono as a precision signal, never as a brand crutch.** Used for tool names, identifiers, shortcuts, timestamps, trace output — ~15% of rendered text.
4. **Spring-based motion in the 150–280ms range**, with a distinct "breathing" idle state on active agent surfaces (2–3s cycle, low-amplitude opacity or scale). No spinners.
5. **Structured artifacts, not chat bubbles.** Responses render in native blocks — diffs, file cards, plan trees, timeline nodes — with chat as the thin conversational layer around them.

Axis should occupy the intersection of all five, with **ink-cobalt #3340E6** as its unclaimed accent, a **dark-first zinc neutral** surface stack, a **Söhne/Inter + Berkeley/Commit Mono** type system, and **structured diff-first artifacts** as the core agent output. That positioning reads as "considered cross-system executor" — the category Axis actually competes in — without being confused for Linear, Claude, Cursor, or Workbench.

---

## 2. Full alternative visual system

### 2a. Color

Axis uses a zinc-tinted dark-first palette layered by luminance, with a single ink-cobalt accent. The palette below is tokenized; every UI rule references token names, not hex, so theming and future color refinement are cheap.

**Design tokens — dark (canonical) and light (mirror)**

| Token | Dark | Light | Usage |
|---|---|---|---|
| `bg.canvas` | `#09090B` | `#F7F6F3` | Outermost page background |
| `bg.surface` | `#111113` | `#FFFFFF` | Cards, panels, chat surface |
| `bg.elevated` | `#1A1A1D` | `#FAFAF8` | Modals, popovers, elevated menus |
| `bg.sunken` | `#060608` | `#EFEDE8` | Inner wells, code blocks |
| `border.subtle` | `#27272A` | `#E7E5E0` | Default hairlines |
| `border.default` | `#3F3F46` | `#D4D1CA` | Inputs, buttons, cards |
| `border.strong` | `#52525B` | `#A8A49A` | Focused, selected |
| `text.primary` | `#FAFAFA` | `#0E0E10` | Headings, body |
| `text.secondary` | `#A1A1AA` | `#55545A` | Captions, metadata |
| `text.tertiary` | `#71717A` | `#89878F` | Placeholders, deep metadata |
| `text.inverse` | `#09090B` | `#FAFAFA` | On-accent, on-filled |
| `accent.primary` | `#4F5AF0` | `#3340E6` | Primary CTAs, focus rings |
| `accent.hover` | `#6B74F3` | `#202CD4` | Hover state of primary |
| `accent.subtle` | `#1C1E3D` | `#E8EAFE` | Accent backgrounds, selected rows |
| `accent.on` | `#FFFFFF` | `#FFFFFF` | Text on accent fills |
| `success` | `#34D399` | `#059669` | Success, healthy connector, run OK |
| `warning` | `#F5A524` | `#B45309` | Attention, rate-limit, stale |
| `danger` | `#F87171` | `#DC2626` | Destructive, auth-expired, failed |
| `info` | `#60A5FA` | `#2563EB` | Neutral informational only |

**Agent-state colors (semantic, never reused for anything else)**

| State | Token | Dark | Light | Signal |
|---|---|---|---|---|
| Thinking | `agent.thinking` | `#9CA3F7` | `#6366F1` | Soft indigo shimmer — reasoning |
| Running (tool-call) | `agent.running` | `#4F5AF0` | `#3340E6` | Primary accent — actively acting |
| Awaiting permission | `agent.awaiting` | `#F5A524` | `#B45309` | Amber — user attention needed |
| Recovered from error | `agent.recovered` | `#34D399` | `#059669` | Green — self-healed |
| Blocked / failed | `agent.blocked` | `#F87171` | `#DC2626` | Red with icon — dead-end |
| Backgrounded | `agent.background` | `#71717A` | `#89878F` | Muted — running out of focus |

**Why this palette and why this accent.**

The accent is **ink-cobalt `#3340E6`** in light mode, **`#4F5AF0`** in dark (luminance-lifted 5% so the hue doesn't get swallowed). Cobalt was chosen against four alternatives:

- **Orange** — rejected. Claude and cultural ChatGPT associations make it tribal. Also reads "warning" in tool-call contexts, which conflicts with its role as primary CTA.
- **Violet/iris #5E6AD2** — rejected. Linear owns this territory so completely that any product using it from 2024 onward reads as an imitator. Shifting hue to `#6366F1` (Tailwind indigo-500) only partly rescues this — still in Linear's neighborhood.
- **Green #3ECF8E** — rejected as primary. Semantically it should remain reserved for success/running states. Promoting it to primary steals vocabulary from the agent-state system.
- **Ink-cobalt #3340E6** — selected. Sits between "serious blue" and "decisive violet," carries structure + intelligence without the Linear-lock-in, and is genuinely unclaimed in the AI agent category. It holds 4.5:1 on both `#09090B` and `#FFFFFF`, survives as a fill color without retuning, and reads immediately as "considered, premium, decisive."

Zinc neutrals (Tailwind's zinc range: `#09090B`, `#18181B` → we use `#111113`) beat pure black for OLED banding reasons and beat slate/navy for reading "calm neutral" rather than "corporate blue." Light mode's `#F7F6F3` is a warm-white that is deliberately not `#F4F3EE` Pampas (Claude's territory) — it's slightly less yellow, slightly cooler, and reads as "paper" without reading as "cream."

### 2b. Typography

**Stack.** Söhne (licensed, preferred) or Inter Display + Inter (free fallback) as the sans; Berkeley Mono (licensed, if budget and product constraints allow) or Commit Mono (OFL free, characterful) as the mono. **No Instrument Serif, no Geist.**

```
--font-display:  "Söhne", "Inter Display", -apple-system, BlinkMacSystemFont, sans-serif;
--font-sans:     "Söhne", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono:     "Berkeley Mono", "Commit Mono", ui-monospace, "SF Mono", Menlo;
--font-numeric:  "Söhne"; /* with tabular-nums feature */
```

**Why not Geist.** Geist is free and well-engineered, but it carries strong Vercel-template brand gravity in the designer/developer audience Axis is selling to. Using it subtly flags "we ship on Vercel's defaults" — not the position Axis wants. Inter is generic enough to be invisible; Geist is generic enough to be tribal.

**Why not Instrument Serif.** It's editorial, ornamental, in active backlash, and tonally signals "AI essay" rather than "AI executor." If a serif accent is ever needed (long-form report rendering), use **Tiempos Text (Klim)** — never Instrument.

**Type scale.**

| Role | Size | Line-height | Letter-spacing | Weight | Font |
|---|---|---|---|---|---|
| Display XL | 48px / 3rem | 1.05 | -0.03em | 500 | Display |
| Display L | 36px / 2.25rem | 1.1 | -0.025em | 500 | Display |
| Display M | 28px / 1.75rem | 1.15 | -0.02em | 500 | Display |
| Heading 1 | 22px | 1.25 | -0.015em | 600 | Sans |
| Heading 2 | 18px | 1.3 | -0.01em | 600 | Sans |
| Heading 3 | 15px | 1.35 | -0.005em | 600 | Sans |
| Body L | 16px | 1.55 | 0 | 400 | Sans |
| Body | 14px | 1.5 | 0 | 400 | Sans |
| Body S | 13px | 1.45 | 0.005em | 400 | Sans |
| Caption | 12px | 1.4 | 0.01em | 500 | Sans |
| Micro | 11px | 1.35 | 0.04em | 500 | Sans (uppercase ok here) |
| Mono L | 14px | 1.5 | 0 | 400 | Mono |
| Mono | 13px | 1.5 | 0 | 400 | Mono |
| Mono S | 12px | 1.45 | 0 | 400 | Mono |
| Kbd | 11px | 1 | 0.02em | 500 | Mono |

**Usage rules.**

- **Display** is used only for empty states, onboarding steps, marketing-adjacent moments, and the first line of a new run ("What should Axis do?"). Never in nav, never in repeated UI chrome.
- **Sans** handles everything else in the app — headings, body, buttons, nav, chat.
- **Mono** renders: tool-call names, tool arguments, file paths, identifiers (IDs, hashes, short tokens), timestamps in run trees, keyboard shortcut chips, streaming trace output, code blocks, diff viewers. Target: ~15% of rendered text. **Never in H1-H3 or body paragraphs.**
- **Tabular numerals** on all counts, durations, token counts, metric values, table columns. `font-variant-numeric: tabular-nums` is applied via a utility class `.num`.
- **Uppercase only in Micro size with +0.04em tracking** — status pills, section labels in admin views. Nowhere else.

### 2c. Spacing, radius, elevation, motion

**Spacing scale (4px base).** `0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 80`. Everything in the product aligns to 4px. Gutters 16px mobile / 24px desktop. Card padding 16–20px.

**Radius.** `none 0`, `xs 4px`, `sm 6px`, `md 8px` (default), `lg 12px` (cards, panels), `xl 16px` (modals, drawers), `full 999px` (chips, avatars). Keep the scale flat — mixed radii look sloppy.

**Elevation.** Luminance-layered on dark, shadow-layered on light.

```
Dark:
  e0 (canvas)      — bg.canvas   #09090B
  e1 (surface)     — bg.surface  #111113 + 1px border.subtle
  e2 (elevated)    — bg.elevated #1A1A1D + 1px border.default
  e3 (modal)       — bg.elevated + inset 1px rgba(255,255,255,0.04) + drop shadow 0 24px 48px rgba(0,0,0,0.5)

Light:
  e0 — #F7F6F3
  e1 — #FFFFFF + 1px border.subtle
  e2 — #FFFFFF + shadow 0 1px 2px rgba(14,14,16,0.05), 0 2px 4px rgba(14,14,16,0.04)
  e3 — #FFFFFF + shadow 0 20px 40px rgba(14,14,16,0.12)
```

**Motion system.** Spring-based for arrivals, ease-out for state changes, linear for shimmer.

```
Durations:
  micro      100–150ms   hover, focus, press
  short      180–240ms   color, opacity, small layout
  medium     260–320ms   panel reveal, card entrance
  long       380–440ms   modal, drawer
  ambient    2400ms      breathing idle on active agent
  shimmer    1400ms      streaming shimmer sweep

Easings:
  spring     {stiffness: 300, damping: 30}  for arrivals, panel reveals
  easeOut    cubic-bezier(0.2, 0, 0, 1)     for state transitions
  easeInOut  cubic-bezier(0.4, 0, 0.2, 1)   for in-place morphs
  linear                                      for shimmer loops

What animates:
  - surface entrance (spring, medium)
  - token streaming (fade-in at word boundaries, 100ms easeOut)
  - tool-call card reveal (spring, medium)
  - modal/drawer (easeOut, long)
  - undo toast (spring, medium, auto-dismiss easeIn)
  - breathing on active agent run row (opacity 0.92↔1.0, 2.4s cycle, infinite)

What does NOT animate:
  - layout reflow during token stream (batch to phrase boundary, snap once)
  - every color change (desensitizes)
  - scroll (native only)
  - focus rings (instant)

Respect:
  prefers-reduced-motion: collapses spring to easeOut short,
  disables breathing + shimmer, replaces with static state.
```

### 2d. Iconography

**Library: Lucide** (fork of Feather). Reasons: free, MIT, tree-shakable, 1300+ glyphs, 2px stroke at 24px that scales cleanly to 16/20. Phosphor is its only serious competitor; Lucide wins for bundle size and Next.js DX. Radix icons are too minimal for an agent product with many states.

**Sizing.** Default 16px in nav/UI chrome; 20px in primary CTAs and empty states; 14px inline with body text; 24px in feature placements. Stroke weight: 1.5px at 16px, 2px at 20/24.

**Custom glyphs.** Commission ~12 custom marks: five connector glyphs (Slack, Notion, Gmail, Drive, GitHub) rendered in a unified outline style at Axis's stroke weight (so the connector grid doesn't look like five logos slammed together); five agent-state glyphs (thinking pinwheel, running triangle, awaiting hand, recovered check-with-curve, blocked octagon); plus the Axis brand mark — two orthogonal hairlines crossing at a tick, echoing the product name architecturally.

### 2e. Sound and haptics

A minimal, product-specific vocabulary. Sounds are all 200–400ms, synthesized (no sample cliches), and user-mutable in Settings. Haptics iOS/Android only.

| Event | Sound | Haptic |
|---|---|---|
| Task complete | Two-note minor-to-major resolve, 320ms | Soft single tap |
| Write confirmed | Single muted click, 120ms | Light impact |
| Undo fired | Reverse sweep, 180ms | Light impact (double) |
| Permission granted | Short rising chirp, 160ms | Selection change |
| Permission denied | Low mute thud, 140ms | Medium impact |
| Error | Descending two-note, 280ms | Error notification |
| Breathing idle (optional) | None | None |

Sounds default off for enterprise; on for first-run single-user. Always off when `prefers-reduced-motion` is set (treated as a "reduce sensory" signal).

---

## 3. Every page, redesigned end-to-end

### 3a. App shell

A three-column shell: **LeftNav (240px collapsible to 56px) · Main (fluid) · RightPanel (360px, contextual, optional)**. No status bar. No breadcrumbs.

```
┌─────────────┬────────────────────────────────────────┬──────────────┐
│  LeftNav    │  Topbar  (project selector, ⌘K, user)  │              │
│             ├────────────────────────────────────────┤              │
│  ▸ Home     │                                        │  RightPanel  │
│  ▸ Chat     │                                        │  (context)   │
│  ▸ Activity │                                        │              │
│  ▸ History  │               Main content             │  e.g.        │
│  ▸ Memory   │                                        │  - run       │
│  ▸ Projects │                                        │    details   │
│  ─────      │                                        │  - memory    │
│  Connect.   │                                        │  - citations │
│  Team       │                                        │              │
│  Settings   │                                        │              │
└─────────────┴────────────────────────────────────────┴──────────────┘
```

**LeftNav.** Sections: primary (Home, Chat, Activity, History, Memory, Projects) above a divider; settings-adjacent (Connections, Team, Settings) below. Each item is a 32px row with a 16px Lucide icon, label at Body S, and an optional count pill at the right. Hovered state uses `bg.elevated`; active state uses `accent.subtle` background + `accent.primary` icon + `text.primary` label. No decorative indicators.

**Topbar.** 48px tall, bordered bottom with `border.subtle`. Left: project selector (current project name in Body, caret, click opens switcher). Center: `⌘K` shortcut chip. Right: connector health dot-cluster (5 tiny dots, each a connector), user avatar with dropdown. No search bar — `⌘K` is the search.

**RightPanel.** Slides in from right when context-bearing (viewing a run's details, inspecting a memory, reading citations). Closeable with `Esc` or the same icon that opened it. Never permanent — always earned by context.

**Home (new; replaces Tableau dashboard).** This is the most consequential IA decision: reject the chat-first home. When Axis opens, the user sees an **operations center**:

```
┌──────────────────────────────────────────────────────────┐
│  Good morning, Alex                                      │
│                                                          │
│  Running now (2)                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ▸ Drafting Q3 recap in Notion · 23s · Step 2/4   │   │
│  │   breathing pulse indicator                      │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ▸ Triaging #support inbox · 1m 14s · Step 5/8    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Needs your approval (3)                                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ⏵ Send email to 4 recipients · 12s ago           │   │
│  │ ⏵ Post link to #general · 34s ago                │   │
│  │ ⏵ Merge PR #1287 · 2m ago                        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Connectors  ● Slack  ● Notion  ● Gmail  ⚠ Drive  ● GitHub │
│                                                          │
│  Recent runs  ·  Pinned prompts  ·  Suggested next       │
└──────────────────────────────────────────────────────────┘
```

Chat is one `⌘K` + prompt away, or clicked via the LeftNav Chat item. This reframing is the single biggest Axis differentiator — every competitor opens to an empty prompt field.

### 3b. Login + Signup

Split-screen, light-mode default (enterprise context). Left: 420px auth form. Right: a live, muted "preview canvas" showing a fake agent run happening — breathing pulse, task tree filling in, undo toast appearing and dismissing. Ambient. Never a stock photo.

**Login form.** Email input, password input (with show/hide), `Continue with Google / Microsoft / GitHub` SSO row, small `Log in` primary CTA, `Forgot password` link, `New to Axis? Sign up` footer. All 16px Body, 40px input height, primary CTA full-width.

**Signup form.** Same structure but includes "Work email recommended" hint. Post-signup lands directly in the demo workspace (see §5g Onboarding) — no empty workspace, no dead-end "connect your first app" gate.

**States.**
- Loading: button shows a small centered spinner replaced with the button label opacity 0.5; whole form disabled.
- Error: inline error Body S in `danger` tone below the relevant input with a matching 1.5px left-border accent on the input.
- Post-success: brief 400ms fade to the workspace, no intermediate spinner screen.

### 3c. Chat (the hero surface)

Layout: prompt input pinned at bottom, conversation stack above, contextual `RightPanel` for citations/runs when expanded.

```
┌──────────────────────────────────────────────┬─────────────┐
│  (previous turns, virtualized)               │ RightPanel  │
│                                              │ (citations, │
│  ────────────────────────────────────        │  run graph, │
│                                              │  memory)    │
│  ▸ Drafting Q3 recap in Notion               │             │
│    ▾ Plan (4 steps)                          │             │
│      ✓ Read #product Slack (45 msgs)         │             │
│      ✓ Read Notion: Q3 roadmap (4.2k words)  │             │
│      ● Draft recap (breathing)               │             │
│      ○ Post to #leadership                   │             │
│                                              │             │
│  ┌─[preview card]────────────────────────┐   │             │
│  │ Notion page will be created:          │   │             │
│  │   Q3 Engineering Recap                │   │             │
│  │   (diff rendering, 120 blocks, 3 imgs)│   │             │
│  │ [Confirm ⏎] [Edit ⌘E] [Cancel Esc]   │   │             │
│  └───────────────────────────────────────┘   │             │
│                                              │             │
├──────────────────────────────────────────────┤             │
│  ┌──────────────────────────────────────┐    │             │
│  │ Type a message, or /command          │⏎  │             │
│  │ @notion  @slack  ↾file  🎙         │    │             │
│  └──────────────────────────────────────┘    │             │
└──────────────────────────────────────────────┴─────────────┘
```

**Elements.**
- **Turn stack** virtualizes past turns (use `react-virtual`); day dividers on scroll; messages are not bubbles (no chat-app affectation) — they're left-aligned blocks with a thin 2px left-border in `accent.primary` for agent turns and `border.subtle` for user turns.
- **Live task tree** replaces a linear "assistant typing…" — a collapsed one-liner by default ("Drafting Q3 recap…"), expandable to the full step tree. Each step shows: state dot, label, elapsed duration (mono tabular), and an optional expand-for-tool-IO drawer. See §4 Live task tree.
- **Citations** inline as tiny superscript source chips: `[S1]` clickable → opens RightPanel with the full source. Highlights the cited span in the agent message when the chip is hovered.
- **Preview cards** for writes appear inline before execution (§5c).
- **Undo toasts** appear anchored to the bottom-right of the chat area, 10s default, with the action name and a single `Undo` button.
- **Correction controls** appear on hover of an agent turn: 👍 · 👎 · ⎌ Fix · ⋯ (copy/regenerate/share).
- **Prompt input** is multi-line, auto-resizing (80px min, 240px max before scroll), with `@connector` and `@agent` chips inline, `/` commands, file drop, optional voice toggle.

**States.**
- Empty: Display M greeting ("What should Axis do?") + 3 suggested prompt chips sourced from the project context + the prompt input. No ghost panels.
- Loading/streaming: task tree appears with breathing on the active node; tokens fade in at word boundaries.
- Populated: virtualized history with day dividers.
- Error mid-run: the failing node in the task tree turns `danger`, expands automatically, shows the error and a `Retry` / `Skip` / `Edit plan` triplet inline — the chat does not clear or error out; the run continues after user input.

### 3d. Activity (proactive surfaces + feed)

A reverse-chronological firehose of everything Axis has done or wants to do. Two lanes at the top: **Proactive** (Axis suggesting an action — "You usually summarize #product on Fridays; want me to?") and **Historical** (completed runs, approved writes, denied permissions, corrections).

Rendered as a time-divided list (Today, Yesterday, Earlier this week, …). Each item is a 56px row: connector icon, short prose, actor, timestamp, status pill. Click expands inline (accordion) to show the run tree summary. Filter chips at the top: all / approvals / writes / errors / proactive.

### 3e. History (past runs)

A search+filter table of runs. Columns: run title, project, duration, steps, status, when. Row click opens the run in a full-height modal with the same task-tree + timeline + replay affordances as the live Chat surface, but with scrub controls and export (`Export JSON trace`, `Share link`, `Pin as template`).

Filters: project, connector touched, status, date range, duration buckets. Search is full-text across run title, user prompt, and tool calls. Pagination: infinite scroll with a sticky "jump to date" affordance in the right rail.

### 3f. Connections (5 OAuth tools)

A **canvas view**, not a settings list. Each connector is a large tile (240×160px) arranged in a loose grid with the Axis hairline-tick motif connecting healthy active ones to a central "Axis" node. Each tile shows: connector logo (Axis-styled outline mark), connection state dot, account email/workspace, last-sync timestamp, latency (mono, tabular), scopes granted (glyph row), a tiny sparkline of last-7-days request volume.

Connector tile states:
- **Healthy** — `success` dot, full color logo, sparkline active.
- **Degraded** — `warning` dot, logo dimmed 60%, "rate-limited · retry in 8s" label.
- **Auth-expired** — `danger` dot + a prominent "Reconnect" button in place of the sparkline.
- **Disabled** — `text.tertiary` everything, dashed border, "Connect" CTA.

Click a tile → right-panel slides in with: scopes in detail (toggleable), BYO OAuth credentials (optional), recent requests log (mono, timestamped), and a "Revoke" destructive footer.

### 3g. Credentials (BYO OAuth per tool + per-scope selector)

Per-connector credentials panel lives inside the Connections right-panel. Three sections:

1. **App credentials** — `Client ID`, `Client Secret` (password-masked, reveal icon), `Redirect URI` (copyable, mono). All inputs use the mono font for values. A clear "Using Axis's default app" default state with a "Use my own app" toggle.
2. **Scopes** — a checklist of scopes grouped by capability (Read messages, Read DMs, Send messages, Manage channels, …). Each scope has a short plain-language description, a tier pill (Tier 0/1/2, see §5b), and a last-used-at timestamp if granted. Scopes the user has not granted are unchecked with a "Request scope" CTA.
3. **Usage** — last 7-days request count, error rate, average latency, rate-limit headroom. All mono/tabular.

### 3h. Memory (3-tier inspector)

Three visible tiers: **Pinned** (user-authored, durable), **Episodic** (run-derived, decaying), **Semantic** (extracted patterns). Each tier is a collapsible section in a searchable list.

```
┌──────────────────────────────────────────────────────────┐
│  Memory                                                  │
│  [Search memory…]       [+ Add memory]    [Bulk clear…]  │
│                                                          │
│  ▾ PINNED · 12                                           │
│    📌 Prefers TL;DRs under 80 words                     │
│    📌 Slack handle is @alex.k; never @alex              │
│    📌 Always skip the #random channel in recaps         │
│                                                          │
│  ▾ EPISODIC · 248 (decay: 30d half-life)                │
│    ● 2d ago · Drafted Q3 recap (ref: run_a9x)           │
│    ● 4d ago · Triaged 47 emails (ref: run_b2k)          │
│                                                          │
│  ▾ SEMANTIC · 34                                         │
│    ◆ Patterns: summarizes on Fridays (n=12)              │
│    ◆ Tone: prefers plain, no emoji in Slack              │
└──────────────────────────────────────────────────────────┘
```

Row hover reveals: `Forget`, `Pin` (if episodic/semantic), `Promote to project memory`, `View source run` (if episodic). Bulk clear is a modal with per-tier selector + type-to-confirm.

**"What does Axis know about me?"** surface: a dedicated `⌘K → what Axis knows` command opens a right-panel summary: "Axis is using 12 pinned memories + 8 recent episodic + 5 semantic patterns relevant to this project." Before a run, this panel can be pinned open so the user sees what's being consulted.

### 3i. Settings

Single-page tabbed layout (tabs at top, content scrolls). Tabs: **Account · Appearance · Capabilities · Output quality · Notifications · Advanced · Sign out**.

- **Account** — name, email, workspace, plan, billing.
- **Appearance** — theme (System / Dark / Light), density (Comfortable / Compact), font scale (90–110%), motion (full / reduced / off), sound (on / off).
- **Capabilities** ("What Axis can do") — the critical panel. A connector-by-connector table with **Read / Draft / Send / Destructive** columns, each a dropdown: `Ask every time` | `Auto for reversible` | `Auto` (with Tier-2 always gated). Shows last-changed-at and who changed it. Default row tops the list: "Apply these to all connectors: [Strict · Balanced · Trusted]."
- **Output quality** — per-project sliders: *Conciseness* (terse ↔ detailed), *Tone* (neutral ↔ friendly ↔ formal), *Citations* (none ↔ always), *Model* (Fast / Balanced / Max), *Think-step budget* (low / medium / high). All changes preview against the last 3 outputs in a mini rendering.
- **Notifications** — per-event toggles for approvals needed, runs complete, errors, weekly summary.
- **Advanced** — API keys (dev use), export data, delete workspace.

### 3j. Team

Reject the org-chart graph. An org chart is visual theater that adds no information a 4-column table doesn't convey. Replace with a **members table** + a **role matrix**.

Members table: avatar, name, email, role, connectors, last active. Invite row at top with email input + role selector + `Send invite`.

Pending invites section below with `Resend` and `Revoke` actions.

Role matrix (below the table): a small table showing what each role can do (View runs, Approve writes, Connect apps, Manage team, Manage billing). No inventing an org-chart metaphor.

### 3k. Projects / New Project

**Projects list.** A searchable grid (3-column at wide, 1 at narrow). Each project card: project name, icon (monogram or user emoji), description, connectors attached, 7-day run count sparkline, last-active-at. Click to switch; right-click for context menu.

**Project switcher.** `⌘P` opens a command-palette-style floating list: search, pinned at top, recent below, "Create project" footer. Replaces both the modal and the sidebar list for switching (retained in LeftNav as an entry point, not the primary mechanism).

**New Project flow.** A single full-height modal with three steps: (1) Name + description + emoji, (2) Connectors to attach (can multi-select, uses existing connections), (3) Initial instructions / system prompt (textarea, with templates). Submit → lands in the new project's empty Chat surface with a demo prompt suggestion.

### 3l. Admin dashboard (from the async-indexing-admin spec)

This is where the original Tableau aesthetic was *closest* to correct — admins do read metrics. But the layout should still favor Axis's system over admin-dashboard clichés.

Three stacked sections:

1. **System health** — 5 KPI cards (indexing backlog, avg run latency, error rate, connector uptime average, active runs). Each card is minimal: single large tabular number in Display M, one-line label Body S, a 7-day sparkline below in `accent.subtle`, a delta pill at the top-right. No "all 12 widgets" noise.
2. **Connector health matrix** — rows: connectors; columns: request volume / error rate / p50 latency / p99 latency / last incident. All mono tabular, sortable.
3. **Eval trends** — line chart of accuracy/quality over time, per-eval-suite, filterable by window. Below: a table of recent regressions with click-through to the example-level trace.

No gradient fills. No pie charts. No legend-happy defaults. One accent color for primary series, a secondary `text.secondary` for baselines.

---

## 4. Every component

All components reference the tokens in §2. Below is condensed spec — enough to build from.

### Buttons

| Variant | Use | Dark fill | Text | Border | Notes |
|---|---|---|---|---|---|
| Primary | CTA | `accent.primary` | `accent.on` | none | 40px tall default; 32px sm; 48px lg |
| Secondary | Companion | `bg.elevated` | `text.primary` | `border.default` | Same sizes |
| Ghost | Tertiary | transparent | `text.secondary` | none; hover `bg.elevated` | Nav/toolbar |
| Danger | Destructive | `danger` | white | none | Same sizes; requires confirm |
| Icon | Toolbar | transparent | `text.secondary` | none; hover `bg.elevated` | 32px square |
| Split | Primary + menu | `accent.primary` | `accent.on` | 1px left divider on caret | `⌘⏎` vs `⌘⇧⏎` |

States: `hover` (slight lift in lightness), `active` (1% darker), `focus` (2px `accent.primary` ring offset 2px), `disabled` (50% opacity, `cursor: not-allowed`), `loading` (label replaced by 14px spinner, width preserved).

### Inputs

40px height, 12px horizontal padding, 8px vertical. Border `border.default` → `accent.primary` on focus + 3px accent ring at 20% alpha. Placeholder `text.tertiary`. Body size.

Variants: plain, with leading icon (16px, `text.secondary`, 8px gap), with trailing icon, with helper (Caption below at `text.secondary`), with error (border + helper in `danger`, left 2px accent bar). Textarea: min 80px, max 240px auto-resize. Password: reveal eye toggle. Email: `inputmode="email"` and auto-capitalize off.

### Selects, comboboxes, multi-select chips

Select uses Radix Select primitive styled to match inputs. Combobox uses `cmdk` (Paco Coursey's library) — fuzzy search with keyword boosts, recent at top. Multi-select chips: selected items render as removable `accent.subtle` chips inside the input; typing filters, `Enter` adds, `Backspace` on empty removes last.

### Cards

Base: `bg.surface`, `border.subtle`, radius `lg`, padding 16px. Variants: `hoverable` (cursor pointer + `border.default` on hover), `interactive` (adds 2px `accent.primary` focus ring), `disabled` (60% opacity, no border change on hover), `with-header` (16px padded header, `border.subtle` bottom), `with-footer` (mirror), `with-toolbar` (header with right-aligned icon buttons, 32px).

### Modals

Four patterns: **standard** (centered, max-w-480, e3), **confirmation** (centered, max-w-400, single focused action), **full-height drawer** (right-slide 480px, runs / memory / credentials), **slide-over panel** (right-slide 360px, lighter, for contextual inspection). All use `Esc` to close and trap focus. Backdrop `rgba(0,0,0,0.4)` with a 200ms fade.

### Toasts

Anchored bottom-right, stack vertically up to 3, 360px width, e2 elevation + 1px border.

| Variant | Icon | Border-left | Use |
|---|---|---|---|
| Info | ℹ | `info` | Neutral status |
| Success | ✓ | `success` | Completed |
| Warning | ⚠ | `warning` | Rate-limit, degraded |
| Error | ✕ | `danger` | Failure |
| Action | ⎌ | `accent.primary` | Undo toast — primary Axis toast |
| Progress | ● | `agent.running` | Long-running background action with determinate or breathing bar |

Action toasts have a single text button at the right ("Undo") plus a close icon. Default dismiss 10s; hovering pauses dismiss; action-required toasts have no auto-dismiss.

### Badges / pills

Default 20px tall, 8px horizontal, radius `full`, Caption size, tabular numerals for counts. Tones: neutral, accent, success, warning, danger, info, agent-state. With-dot variant: a 6px `●` on the left. Sizes: `sm` 16px, `md` 20px, `lg` 24px. Uppercase variant is reserved for Micro label with +0.04em tracking — used sparingly on admin surfaces only.

### Tables

Row height 40px default, 32px dense. First column sticky on horizontal scroll. Header row: `text.secondary`, Caption, uppercase optional, sticky on vertical scroll. Zebra striping off by default; use `border.subtle` between rows. Row hover: `bg.elevated`. Row-actions column: right-sticky, icon buttons only, appear on hover (persistent on touch). Pagination: "Page 1 of 12 · 100 rows · ←/→" at the bottom-right, mono/tabular. Empty state inside the table body per §6.

### Lists

Three variants: **stacked** (no dividers, 12px gap), **divided** (`border.subtle` between items, 0 gap), **interactive** (cursor pointer, `bg.elevated` hover, keyboard-focusable). Standard row: 48px tall, 12px horizontal padding, leading 16px icon + label + metadata right.

### Diff viewer

The single most important agent component. Mono-first, three-line types: `+` (added), `−` (removed), `=` (unchanged context). Per-hunk accept/reject icons at the right. Copy button at the top-right of each file. Rollback button in the card footer when a previously-applied diff is being viewed post-execution.

```
┌─────────────────────────────────────────────────────┐
│  notion://pages/q3-recap              ⎘ Copy  ⎌ Revert │
├─────────────────────────────────────────────────────┤
│  ·  # Q3 Engineering Recap                          │
│  +  Shipped: agent-runtime v2, 3 new connectors…    │
│  −  Shipped: agent-runtime v2.                      │
│  ·                                                  │
│  +  ## Highlights                                   │
│  +  - 43% latency reduction                         │
│  +  - …                                             │
└─────────────────────────────────────────────────────┘
```

For unstructured writes (emails, Slack messages), the diff viewer degrades to a rendered-body view with recipient pills at top and a "view plain" toggle.

### Live task tree

Columnar step list with state dots (see §2a agent-state colors). Each step row: dot · label · duration (mono, tabular, right-aligned). Expand carets reveal tool-call IO in a nested panel with the tool name (mono), arguments (mono JSON, collapsible), and result (mono, truncated at 10 lines with "View all"). Active row has the breathing idle animation on the dot and label at 92% opacity.

```
▾ Plan · 47s
  ✓ Read #product Slack                  3.2s
  ✓ Read Notion: Q3 roadmap              5.8s
  ● Draft recap                         [breathing]
    ▾ tool_call: notion.create_draft
       args: {title: "Q3 Engineering Recap", …}
       → draft_id: "n_29xk2…"
  ○ Post to #leadership                   —
```

### Citations

Two presentations: **inline** (superscript `[S1]` mono chip on the cited span) and **panel** (RightPanel source list with title, snippet preview, connector icon, opened-in-new affordance). Hovering a chip dims all other chips and highlights the cited span.

### Command bar / prompt input

Multi-line auto-resize textarea (80px → 240px). Left: `+` attach menu (file, image, connector source). Right: voice toggle (if enabled), send button (`⏎`). Above the textarea: slash command popover (`/summarize`, `/draft`, `/search`, `/rerun`, `/clear`). Below: quiet helper row with `@connector` suggestions and shortcut hints.

`⌘⏎` sends; `Shift⏎` newlines; `Esc` clears when non-empty, closes when empty.

### Segmented controls

2–4 segments, equal width, 32px tall, `bg.elevated` container with a single sliding `accent.subtle` indicator (280ms spring). Text `text.secondary` default, `text.primary` when active. Use for small mode switches (e.g., diff view: `Inline / Side-by-side`).

### Tabs

Underline style. 40px tall, Body S weight 500. Inactive `text.secondary`; active `text.primary` with a 2px `accent.primary` underline. No background pills (pills read as buttons). Keyboard: ←/→ navigates, `Enter` activates.

### Progress indicators

Four types:
- **Determinate bar** — 4px tall, `accent.subtle` track, `accent.primary` fill, ease-out on width change.
- **Indeterminate shimmer** — for unknown-length work. A gradient sweep across the element at 1400ms linear. Use when steps are unknown; otherwise prefer determinate.
- **Step progress** — "Step 2 of 4" label with a 4-dot indicator, filled up to the active dot.
- **Skeleton loaders** — `bg.elevated` blocks with a shimmer sweep at 1400ms. Use for content shape, not spinner replacements.

**No spinners** on primary surfaces. Spinners are allowed only inside buttons mid-submit and inside icon-buttons during small fetches.

### Avatars + initial circles

32px default, 24px compact, 40px large, 56px hero. Shapes: `circle` for humans, `squircle` (radius `md`) for agents/bots. Agent avatar: `accent.subtle` fill with the Axis hairline-tick mark in `accent.primary`. Initial circles: deterministic hue-pair from a curated 8-color palette (none of which is the primary accent) with white text, 500 weight.

### Breadcrumbs

**Killed.** Agents don't work in path hierarchies; the mental model is "project → run → tool call" and the task tree already exposes that. The few places that currently use breadcrumbs (settings subpages, admin dashboards) get a back-arrow + parent-label pattern instead, which is shorter and clearer.

### Tooltips, popovers, dropdowns, context menus

Tooltip: 24px tall, `bg.elevated`, Caption, 4px radius, 600ms hover delay, disappears instantly. Popover: Radix Popover styled to e2. Dropdown: Radix DropdownMenu, 32px row height, Body S, leading icon optional, trailing shortcut mono chip. Context menu: right-click and `Shift F10`, same styling as dropdown, divider-separated sections.

### Empty states

One "blank canvas" system across all pages. A centered card with: a 48px Lucide icon in `text.tertiary`, Display M title, Body S subtext (max 2 lines), and 1–2 action buttons. The icon uses the Axis hairline-tick motif style, not a decorative illustration. Varies by page only in the icon, title, subtext, and actions — never in layout.

### Error states

Per §6. Three levels: inline (on a specific field/row), card (replacing the affected component), page (blocking). Each shows: icon + short cause + suggested action + retry affordance. Never "Something went wrong."

### Keyboard shortcut overlay

`?` opens a full-screen overlay (scrim `rgba(0,0,0,0.6)`) with a searchable, categorized shortcut list. Categories: Global, Chat, Run, Permissions, Memory, Navigation. Each row: shortcut chip (mono `Kbd`) + action label. Search filters in real time.

---

## 5. Interaction patterns

### 5a. Agent prompt + run

**Submit.** User types in the prompt input; `⌘⏎` submits. On submit, the input collapses to a non-editable compact summary line above the task tree, with an `Edit` icon to revise the prompt (which creates a new turn, not edits the in-flight one).

**Task tree grows live.** The plan arrives as soon as the model produces it (often within 1s). Each step enters with a spring reveal; the active step gets breathing idle. Tool calls expand inline under their step. Token streaming appears in the current step's panel in word-batched fade-ins.

**Citations inline.** As the agent produces cited claims, superscript chips appear inline. The RightPanel auto-expands the first time a citation appears in a session; subsequent citations do not auto-expand.

**Error mid-run.** The failing step's dot turns `danger`, the node auto-expands to show the error, and an inline triplet appears: **[Retry] [Skip] [Edit plan]**. Axis does not abort the run. `Edit plan` opens a small inline plan-editor (textarea pre-filled with the current remaining plan, editable) → resubmit continues from the chosen step.

**Cancel.** `⌘.` cancels the current run. Any partial writes that have not been confirmed are discarded; confirmed writes remain with their undo windows.

### 5b. Permission confirmation (A1)

**Recommendation: Option B "Allow + Just once + Change scope" inside an Option C inline-in-chat card**, gated by a three-tier risk model.

The UI:

```
┌─[permission card]────────────────────────────────────────┐
│  Axis wants to use Notion → Create page                  │
│  Scope: pages:write · this project                       │
│                                                          │
│  [ Allow ⏎ ]   Just once (⌘J)   Change scope…    ✕      │
│  ☐ Always allow for this project                         │
└──────────────────────────────────────────────────────────┘
```

- **Allow** (primary, `⏎`) — grants the scope for the duration of the session.
- **Just once** (ghost, `⌘J`) — grants for this tool-call only.
- **Change scope…** (text link) — opens a popover with per-scope checkboxes.
- **Deny** (`✕` icon, `Esc`) — denies, halts the step, offers `Edit plan`.
- **Always allow for this project** — checkbox, project-scoped (never global), expires after 30 days of non-use.

**Why B inside C.** Option A (single Allow+Deny + popover) treats every prompt the same and burns goodwill on repeats. Option D (keyboard-first alone) invisibilizes for mouse users and fails accessibility. Option C (inline card) is the correct container — modals break conversational flow and toasts are too ephemeral for approvals. Option B supplies the right button semantics: a sensible default, a low-commitment escape hatch, and an on-ramp to fine-grained control. The composite mirrors iOS 18 / Android 15 one-time-vs-always consent and matches Google's incremental-auth guidance.

**Three tiers gate which card shows up.**

| Tier | Actions | Treatment |
|---|---|---|
| 0 — Read | List, search, read, preview | Pre-approved at connector install; no per-action prompt; logged silently in run timeline |
| 1 — Reversible writes | Draft, create, comment, post-to-DM, create-event | Inline card with B semantics above |
| 2 — Irreversible / blast-radius | Send email >3 recipients, @channel, delete, force-push, merge, external share, pay | **Modal with type-to-confirm** + audience warnings; never bypassable by "Always allow" or trust mode |

**Edge cases.**

- **Rapid repeat requests.** After ≥10 approvals of the same tool-call type in a project with ≥90% approval rate, surface a passive offer: "You've approved this 12 times. Always allow for this project?" Never auto-enable.
- **Batch permissions (agent asks for 3 tools at once).** Show a single **Plan card** at the top of the run with all Tier-0/1 steps listed + risk pills. One **Approve plan** click covers them. Tier-2 steps within still re-prompt individually.
- **First-time vs Nth-time.** First-time permission cards include a short "What this means" Body S line. Nth-time (same session) drops it.
- **Denied-then-asked-again.** The second time the agent tries a path the user denied, the card surfaces the denial history: "You denied this 2 minutes ago. Deny again or Allow?"
- **Expired grants.** At 30-day non-use, the grant silently expires. Next attempt shows the full card with an "Expired · was previously allowed" badge.
- **Prompt-injection suspicion.** If the run-transcript classifier flags suspicion (Claude-style), the card forcibly downgrades to plain Allow/Deny with a red warning banner and no "Just once" / "Always" options.

### 5c. Write confirmation (A2)

**Recommendation: Option B "inline preview card with Confirm/Edit/Cancel then undo toast" as default, with Option D "trust mode per connector" as a user preference overlay. Irreversibles always hard-gated regardless.**

The preview card:

```
┌─[write preview]──────────────────────────────────────────┐
│  Gmail · Send draft                                      │
│  To:   jane@company.com, team@company.com  (2)           │
│  Subj: Q3 Engineering Recap                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Hi team, here's the Q3 recap…                      │ │
│  │ [diff / render view]                               │ │
│  └────────────────────────────────────────────────────┘ │
│  [ Confirm ⏎ ]   Edit (⌘E)   Refine…   Cancel (Esc)    │
└──────────────────────────────────────────────────────────┘
```

- **Confirm** — executes. On success → card transforms to "Sent" state + undo toast (10s for interactive, 30s for scheduled). On failure → card transforms to "Failed — [Retry] [Edit] [Cancel]" with explanatory error.
- **Edit** — inline editor (textarea with pre-filled content) → save returns to preview.
- **Refine…** — sends content back to the model with a short instruction ("more concise", "formal tone").
- **Cancel** — discards.
- **Per-connector trust mode** (Settings → Capabilities) can relax *Tier 1 only* to "Preview, auto-confirm after 5s" or "Auto for reversible." Tier 2 ignores trust mode entirely.

**Why B + D.** Option A (always-optimistic with 30s undo) lies — some writes genuinely cannot be undone, and an undo that sometimes fails destroys trust more than friction does. Option C is functionally B. Option D alone skips the core affordance (see-before-commit). B + D is the honest composition: default to preview, let users dial friction per connector, and never let trust mode touch irreversibles.

**Edge cases.**

- **Write fails halfway.** Card shows partial state: "Notion page created (id: n_29xk…). Slack post failed (rate-limited). [Retry Slack] [Skip Slack] [Cancel remaining]." Never silent auto-rollback — users hate invisible state more than explicit half-failures.
- **Write succeeds but connector reports later error.** Reconcile visibly: card moves to "Failed after send — [View details]" and logs to the run timeline. Do not pretend success.
- **Undo fails.** Toast transforms to a compensating-action prompt: "Message already delivered. [Delete from Slack] [Send retraction] [Dismiss]." Honest.
- **User offline when executing.** Offer `Queue this action — retry when online` and show it in a persistent "Queued actions" tray in the topbar.
- **Audience >3 recipients on email.** Upgrade to Tier 2 modal with a recipient-list review: each recipient pill shows internal/external status; externals flagged. Type-to-confirm with the word `send`. Cannot be bypassed by trust mode.
- **Cross-connector cascades (draft in Notion, post link in Slack).** Saga pattern: execute in risk order (cheapest-to-undo first — Notion create, then Slack post). Label the undo toast honestly: *"Undo will delete the Notion page. The Slack post cannot be unsent by Axis. [Undo Notion only] [Send retraction in Slack]"*. If step 2 fails, surface the half-success: "Notion draft created. Slack post failed. [Post now] [Delete Notion page] [Keep as is]."

### 5d. Correction capture

Four layers, in order of specificity.

1. **Thumbs + reason chips** on every agent turn. 👎 expands a 4-chip picker inline: *Wrong · Tone · Missed info · Wrong action*. One click records the score; optional "Add note" one-line text.
2. **Rich selection correction.** User highlights a wrong span in the agent message → a floating popover offers "Fix this" → inline editor with the selected text pre-filled. Saving captures the diff as a `corrective_edit` training signal.
3. **Preview-card edits.** Any Edit made in a preview card (§5c) is captured as diff-level feedback — highest-value training signal because it pairs agent proposal with user correction.
4. **Silent telemetry.** Copy-vs-ignore, regenerate counts, tool-call acceptance rate, time-to-first-edit, undo usage per action type, abandoned-mid-run rate. All logged server-side, no UI.

**Closing the loop.** Weekly, if the user has made ≥3 corrections of the same shape, surface: *"You corrected Axis on email tone 3 times this week. Want to set a preference?"* — converts recurring corrections into pinned memories (§3h).

### 5e. Project switching

**Recommendation: command-palette style (`⌘P`)** as primary, sidebar list as secondary entry point.

`⌘P` opens a floating searchable panel: search field, pinned projects at top, recent below, "Create project" footer. Fuzzy search; keyword boosts. `⏎` switches; `⌘⏎` opens in new tab. The LeftNav still lists 5 most-recent projects as a shortcut for mouse users, but the keyboard palette is the primary mechanism.

Reject the modal approach (too much friction for what is a frequent operation) and the persistent dock icon (wastes sidebar real estate for 50+ project workspaces). Command-palette scales from 3 to 500 projects without re-design.

### 5f. Memory inspection + edit

**View a memory.** Click the row in Memory (§3h) → RightPanel slides in with full content, source run(s), creation date, last-used-at, confidence (for semantic), and a `Usage log` showing recent runs that consulted it.

**Forget.** Hover row → trash icon. Click → inline "Forgotten · Undo" toast with 10s undo. After 10s, soft-deleted for 30 days then hard-deleted. Pinned memories require a confirm step.

**Add.** `+ Add memory` button opens a textarea; saves as Pinned. Accepts markdown for structured memories.

**Pin.** Hover row → pin icon → promotes episodic/semantic to Pinned. Can be done from within a run as well ("This is important — remember this" command).

**Bulk clear.** Modal with per-tier selector (Pinned / Episodic / Semantic / All), preview of count, type-to-confirm with the word `clear`.

**"What Axis knows right now" surface.** A `⌘K → what Axis knows` command opens the RightPanel with a condensed view: counts per tier, top 5 most-used pinned memories, relevant episodic memories for the current project, and any semantic patterns flagged as high-confidence. This panel can be pinned open during a run — the active memories highlight in real-time as the agent consults them.

### 5g. Onboarding (first 5 minutes)

**Minute 0–1.** No gate. The user lands in a **pre-populated demo workspace** with synthetic Slack/Notion/Gmail data. The prompt input is pre-filled with a suggestion: *"Summarize yesterday's #product channel and draft a Notion recap."* One click submits. The agent runs entirely on synthetic data, plan tree streams in, preview card shows the draft, user clicks Confirm, synthetic Notion page appears in a right-panel preview. Full end-to-end success in ≤90s.

**Minute 2–3.** A single gentle prompt: *"Connect your first workspace to run this on your real data."* One connector (Notion default, based on the demo they just saw). Narrowest scope. Skip button is always present — demo is fully functional indefinitely.

**Minute 3–5.** At the moment a connector is needed, a just-in-time chip appears inline in the next run: *"Want to pull real Gmail into this recap? Connect Gmail"* — Google's incremental-auth principle applied as UX.

**Deferred.** Team features, admin policies, multi-connector plans, memory setup, preferences. They surface via tooltips after first use, never before.

### 5h. Multi-tool agent runs

Use the **two-level collapsible view** described in §3c/§4.

- Default (collapsed) is a one-line status with determinate progress when steps are known, breathing shimmer when exploratory.
- Expanded is task-tree (left) + timeline scrubber (bottom) + tool IO detail pane (right). Nodes color-coded by type: read (neutral), write (accent), external (warning tone), error (danger).
- Parallel tool calls render as sibling nodes under a fork marker; timeline duration bars make concurrency visible — copy Replit Agent 4's fork idiom.
- Post-run: persists as an auditable artifact in History, exportable as JSON trace (OpenTelemetry-compatible schema).
- Prose narration lives *inside* a node (the agent's reasoning), never as the primary container.

### 5i. Offline / degraded

**Connector-status chip row** is always visible (collapsed) in the topbar. Each connector is a small dot. Click → details popover with scope status, last request, error rate, and `Reconnect` / `Retry` affordances.

**Inline degradation notices.** When a step is affected, the notice appears inside the run-tree node, not as a modal. Example: `Gmail is rate-limited — retrying in 8s  [skip step]`.

**Model fallback transparency.** When Axis falls back from Max to Fast due to capacity, it says so in-line at the step level: *"Switched to Fast model for this step."* Users accept degraded models if informed; they mistrust silent swaps.

**Queued writes when connector down.** Offer `Queue this action — retry when Gmail recovers`. Queue visible in the topbar "Queued actions" tray; can be cancelled manually.

**Placeholder / stub states** (e.g., Voyage falling back to hash embeddings, scoring stubbed). These appear in the topbar as a subtle `warning` chip: *"Embedding fallback active"* clickable to details. Admin dashboard surfaces the percentage of requests using fallback.

**Error language rule.** Always pair a cause and an action. Bad: *"Something went wrong."* Good: *"Notion is returning errors. Axis will retry in 30s. [Cancel run]"* Bad: *"Auth failed."* Good: *"Your Google Drive token expired on April 15. [Reconnect]"*

### 5j. Keyboard model

Full map, organized by surface.

**Global**
```
⌘K      Command palette
⌘P      Project switcher
⌘/      Focus prompt input
⌘,      Settings
⌘⇧A     Activity
⌘⇧H     History
⌘⇧M     Memory
?       Shortcut overlay
⌘B      Toggle left nav
⌘.      Stop current run
⌘Z / ⌘⇧Z Undo / redo (within undo window)
```

**Chat**
```
⌘⏎      Send prompt
⇧⏎      Newline
Esc     Clear non-empty input (then close input)
J / K   Next / prev tool-node in run tree
⌘↓      Skip to latest message
⌘↑      Top of conversation
⌘R      Regenerate last agent response
⌘E      Edit last user prompt
```

**Permission / preview cards**
```
⏎       Allow / Confirm (primary)
⌘J      Just once
Esc     Deny / Cancel
⌘E      Edit (preview cards)
⌘⏎      Approve all in plan
⌘⇧⏎     Approve all + remember for project
```

**Memory**
```
/       Focus memory search
N       New pinned memory
F       Forget focused row
P       Pin focused row
```

**Run / history**
```
Space   Play / pause replay
←/→     Scrub timeline
⌘S      Save run as template
⌘E      Export JSON trace
```

---

## 6. Edge cases

### First-run empty states (one blank-canvas system)

Single component. Centered card with Axis hairline-tick icon (48px, `text.tertiary`), Display M title, Body S subtext (≤2 lines), 1–2 CTAs. Per page:

| Page | Title | Subtext | Primary CTA |
|---|---|---|---|
| Chat (new project) | "What should Axis do?" | "Try one of these, or write your own." | 3 suggested chips |
| Activity | "Nothing yet" | "Runs, approvals, and agent activity will show up here." | "Start a run" |
| History | "No past runs" | "Your run history appears here once Axis starts working." | "Start a run" |
| Memory | "Axis doesn't know you yet" | "Memories are created as you use Axis. You can also add them manually." | "+ Add memory" |
| Connections | "Connect your first app" | "Axis works across Slack, Notion, Gmail, Drive, and GitHub." | "Connect" |
| Team | "Just you" | "Invite teammates to share projects and runs." | "Invite" |
| Projects | "No projects" | "Projects group related runs, memories, and connections." | "New project" |

### Error states

Three levels — inline, card, page — each with: icon + short cause + suggested action + retry. Taxonomy:

- **Retryable** — "Temporary issue, retrying…" with progress; after 3 retries, escalates.
- **Fatal** — "Axis can't complete this. Here's what we saw: …" with raw error in a mono collapsible.
- **Auth-expired** — specific reconnect CTA.
- **Rate-limited** — specific countdown, skip option.
- **Provider-down** — link to status page + estimated recovery if known.

### Loading states

Skeletons everywhere for content shape (never spinners on primary surfaces). Skeleton block: `bg.elevated` at e1, 1400ms linear shimmer sweep, layout-matched to the eventual content. Avoid layout shift by reserving heights. Shimmer (not pulse) because it reads as "streaming incoming" rather than "pending."

### Very long agent runs (>60s)

After 60s, the run row shows an explicit elapsed counter (mono tabular). After 120s, a non-intrusive `Continue in background?` chip appears in the run tree — clicking moves the run to a background tray (topbar `Running (n)` chip) and the user can continue. Backgrounded runs surface toast when they complete, even if the user is on another page.

### Very short agent runs (<1s)

Defer the task-tree render for 300ms. If the run completes before then, skip straight to the final state without flashing the tree. Streamed tokens under 100ms worth appear in a single fade-in rather than word-by-word.

### Very long chat scrollback

Virtualize with `react-virtual`. Day dividers on scroll, sticky at top during scroll-within-day. `⌘↓` jumps to latest. Search within conversation (`⌘F`) uses the topbar's search and highlights matches with a scrollbar mini-map on the right.

### Large connections (10+)

Switch Connections canvas to a paginated grid at >9 connectors, grouped by health/category. Sparklines shrink. Search input appears at the top.

### Large projects (50+)

`⌘P` project switcher handles this with fuzzy search + recent-weight. Sidebar shows only the 5 most recent; "All projects" link scrolls to the full Projects page.

### Large memory (10k+ episodic rows)

Paginate at 100 per tier with virtualization within a tier. Cluster episodic memories by semantic similarity (lazy clustering, only on open). Search is full-text + semantic over the full store. Bulk operations fan out server-side with a progress toast.

### Small screens

- **Tablet (≥768px)** — LeftNav collapses to 56px icon rail; RightPanel becomes overlay (slides over Main, dismissible).
- **Narrow laptop (1024px)** — RightPanel overlays instead of docking; LeftNav stays expanded.
- **Mobile web (<768px)** — LeftNav becomes bottom tab bar (5 items max: Home, Chat, Activity, Memory, Settings); Topbar slims to 40px; RightPanel becomes full-screen sheet; preview cards become bottom sheets; prompt input pins to bottom with floating send; modals become full-screen.

### Right-to-left

All layouts use logical CSS properties (`margin-inline-start`, `padding-inline-end`, `text-align: start`). Arrow icons mirror; action icons (send, arrow-right) mirror via `[dir="rtl"]` rule. Mono content stays LTR inside the mono block (code is LTR by spec). Progress bars fill start→end regardless of direction.

### Dark/light parity

Every component is speced in both modes, reviewed side-by-side. Accent luminance shifts +5% in dark (#3340E6 → #4F5AF0). Borders go from `#27272A`/`#3F3F46` (dark) to `#E7E5E0`/`#D4D1CA` (light). Shadows disabled in dark, used in light. Parity is a testable property: every screen ships a visual regression test in both modes.

### Color-blind accessibility

Semantic colors are never the sole signal.

- Success — `success` green + ✓ icon + "Done" label.
- Warning — `warning` amber + ⚠ icon + "Review" label.
- Danger — `danger` red + ✕ or ⎊ icon + "Failed" / "Destructive" label.
- Agent states — each has a unique shape (pinwheel, triangle, hand, check-curve, octagon) in addition to color.

All contrast pairs ≥4.5:1 for body, ≥3:1 for large text and UI strokes.

### Screen reader / keyboard-only

- Every interactive element has an `aria-label` or visible label.
- Modal traps focus + returns focus on close.
- Prompt input's streaming response uses the **two-buffer ARIA pattern**: visually-shown buffer is `aria-hidden="true"`; a separate `aria-live="polite"` region receives completed-sentence chunks only. Initialize live region empty on page load (pre-populated regions don't announce reliably).
- `role="status"` for non-critical updates; `aria-live="assertive"` for errors and permission prompts.
- `aria-atomic="false"` on streaming, `"true"` on status toasts.
- Permission card moves focus to Allow button and announces assertively: *"Axis wants to send an email to 4 recipients. Review and confirm."*
- Motion respects `prefers-reduced-motion` — breathing, shimmer, springs collapse to instant or easeOut-short.
- Testing matrix: NVDA+Firefox, VoiceOver+Safari, JAWS+Edge.

---

## 7. Competitive positioning of the design

Axis's design risk is not being too bold — it's being **legible as "yet another 2024 AI vibes product."** Every soft default (Instrument Serif, Geist, warm orange, Pampas cream, #5E6AD2 violet, DM Mono status pills) currently reads as mimicry of an existing winner. The positioning below is the opinionated escape.

| Competitor | Their design | Axis's counter-position |
|---|---|---|
| **Dust.tt** | Dodger blue #1D91FF + cute emoji avatars + chat-first | Ink-cobalt unique accent, hairline geometric agent marks, ops-center home |
| **Glean** | Enterprise blue gradients, search-first | Not a search product; dashboard of *actions*, not results |
| **Claude** | Pampas cream + terracotta + Styrene + Tiempos | Warm-but-not-cream #F7F6F3; sans-first, no serif; decisive not literary |
| **Lindy** | Purple-pink gradients + 3D blobs + mascot agents | Zero gradients, zero mascots, zero sparkles |
| **Notion AI** | Invisible AI, inline slash | Inline *and* visible — breathing on active runs, task trees, preview cards |
| **Cursor** | VS Code chrome + dense IDE density + dark near-black | Not an IDE; no file tree, no tab bar; workspace-grade density |
| **Linear** | #5E6AD2 violet + Inter Display + hairline dark | Adjacent quality tier but ink-cobalt, wider emotional range |
| **Raycast** | Red-coral + launcher form factor + macOS-first | Full app, not a launcher; `⌘K` from anywhere but not the *only* surface |

**Memorable without gimmick.** Five signatures in combination:

1. **Ink-cobalt #3340E6** as the single unclaimed accent.
2. **Hairline-tick "axis" mark** — two orthogonal lines crossing, appearing as the brand mark, empty-state icon, loading indicator, connector-canvas hub, and favicon. Architectural, never decorative.
3. **Operations-center home surface** — no chat box on the home page. This alone separates Axis from every competitor in the category.
4. **Diff-first writes** — every agent modification renders as a before/after diff, copying Cursor's best pattern into workspace-agent territory where nobody else has brought it.
5. **Breathing idle on active agent surfaces** — 2.4s opacity oscillation, low-amplitude, replaces spinners. Tiny, characteristic, invisible until you see it in another product and realize it's missing.

**Where each competitor falls short and how Axis does better.**

- Dust buries integrations in a settings page; Axis gives connections a canvas.
- Glean is search-first; Axis is action-first.
- Claude lacks structured tool-call affordances; Axis's task tree + diff view expose the agent's work.
- Lindy anthropomorphizes; Axis uses geometric non-anthropomorphic agent marks.
- Notion fragments AI into four entry points; Axis has one coherent invocation model.
- Cursor inherits IDE chrome; Axis designs from the workspace-first primitive.
- Linear has no AI-native patterns for streaming, permission, or memory; Axis ships them as first-class.
- Raycast caps at launcher form factor; Axis extends to a full operations surface while keeping keyboard-first parity.

---

## 8. Implementation plan

### Migration order

**Phase 0 — tokens (Week 1)**

File: `tailwind.config.ts`
- Replace current slate/navy/blue palette with the zinc + ink-cobalt palette in §2a.
- Add semantic token layer (`bg.surface`, `accent.primary`, etc.) as CSS variables in `globals.css`.
- Add `agent.*` state tokens.
- Add type scale (§2b) as theme extension.
- Add motion tokens (durations, easings, breathing keyframes).
- Add `--font-sans`, `--font-display`, `--font-mono` CSS variables.
- Ship behind a feature flag `VISUAL_V2` set per-user.

File: `globals.css`
- Define CSS variables for both dark and light themes via `:root` and `[data-theme="light"]`.
- Define `@keyframes breathe` (opacity 1 → 0.92 → 1, 2.4s infinite).
- Define `@keyframes shimmer` (linear translateX, 1400ms).
- Define `prefers-reduced-motion` overrides that disable breathing/shimmer/springs.

**Phase 1 — component primitives (Weeks 2–3)**

Recommendation: move primitives to `packages/design-system` **now**. Reasons: (a) imminent mobile follow-on needs token + primitive parity; (b) future embed/extension surfaces; (c) keeps the web app from accreting bespoke styled components.

Migrate in this order:
1. Button, Input, Textarea, Select (most-used, highest impact).
2. Card, Badge, Toast, Modal, Popover.
3. Tabs, SegmentedControl, Tooltip, DropdownMenu.
4. Avatar, ProgressBar, SkeletonBlock, Kbd.
5. New Axis-specific components: **LiveTaskTree**, **DiffViewer**, **PermissionCard**, **WritePreviewCard**, **CitationChip**, **AgentStateDot**, **ConnectorTile**, **MemoryRow**.

Each component ships with: tokenized styles, accessibility annotations, Storybook entry, dark+light visual test, unit test for keyboard behavior.

**Phase 2 — shell (Week 4)**

- Replace current topbar + sidebar with the 3-column shell (§3a).
- Remove status bar (currently at the bottom) — status moves into the topbar connector chip row.
- Theme toggle in Settings (not topbar — too rarely used to waste shell space).
- `⌘K` command palette using `cmdk` library.
- Keyboard shortcut overlay at `?`.

**Phase 3 — page-by-page migration (Weeks 5–10)**

Order by perceived impact:

1. **Chat (Week 5)** — highest-use surface. New task tree, preview cards, citations, streaming. This alone makes the product feel new.
2. **Home (Week 6)** — operations center replaces old dashboard. Largest perception change.
3. **Permissions + Writes (Week 6, parallel)** — new A1/A2 interaction patterns. Gate rollout behind a second flag.
4. **Connections (Week 7)** — canvas view. High demo impact.
5. **Memory (Week 7)** — 3-tier inspector.
6. **History + Activity (Week 8)** — run tree persistence and feed.
7. **Settings + Team (Week 9)** — capability scope panel is new; rest is cleanup.
8. **Admin dashboard (Week 10)** — ported last because it's internal-facing and least user-visible.

**Phase 4 — mobile follow-on (Weeks 11–14)**

Shared token layer in `packages/design-system` means iOS/Android get the same hex values, radius scale, and motion durations. Native teams mirror:
- Light/dark themes identical to web.
- Type scale — iOS via dynamic type mapped to the scale, Android via resource XML.
- Motion — Core Animation springs (stiffness 300, damping 30) and Android physics-based springs.
- Mono font — Berkeley Mono (if licensed cross-platform) or Commit Mono in both native apps.
- Small-screen patterns from §6 become native-default layouts.

### Risk flags + rollback plan

**Risks.**

1. **Berkeley Mono licensing.** Their terms restrict use inside IDE/editor/terminal products without negotiation. If Axis renders user code in-chrome, this needs legal sign-off. **Mitigation:** default stack uses Commit Mono (OFL free); Berkeley is a drop-in upgrade after license confirmed.
2. **Söhne licensing budget.** Söhne is ~$4–10k. **Mitigation:** Inter Display + Inter is the free fallback and ships well. Upgrade when budget allows — swap is token-level.
3. **Flag-gated rollout.** A two-flag system: `VISUAL_V2` (tokens + chrome) and `INTERACTION_V2` (A1/A2 permission + write models). Independent flags so visual rollout can proceed if interaction work slips.
4. **Visual regression.** Establish a Chromatic or Playwright visual-diff suite *before* Phase 0 lands. Every PR runs diffs in both themes, tablet + desktop.
5. **User disruption.** For existing users, ship with an in-app "What's new" modal on first load after `VISUAL_V2` = true, with a single-click opt-back-to-old for 30 days. Telemetry on revert rate.
6. **Accessibility regressions.** Run axe-core in CI on every PR. New ARIA live-region pattern for streaming is the highest-risk change — ship behind its own flag and test with real screen readers (NVDA+Firefox, VoiceOver+Safari) before rollout.
7. **Custom typography fallback.** FOUT/FOIT risk. Use `font-display: swap` for sans and `optional` for mono (mono content can ship in the fallback without losing meaning; sans cannot).

**Rollback plan.**

- `VISUAL_V2` flag off instantly reverts to old tokens + shell (keep old CSS in place during Phase 0–2; delete only after 60 days stable at 100% rollout).
- `INTERACTION_V2` flag off reverts A1/A2 to current single-modal + optimistic defaults. The new components (`PermissionCard`, `WritePreviewCard`) simply don't render; legacy modals re-render.
- Per-user rollback via Settings → Appearance → "Use classic Axis" (30-day escape hatch).
- Metric gates for auto-rollback: revert rate >15% in 24h, accessibility violations in prod, error rate on new components >2x baseline.

---

## Closing posture

Axis wins this category not by out-chatting the chat apps, but by looking and behaving like **software that does work across your real tools** — with a visible task tree, a diff-first preview of every change, an honest permission and undo vocabulary, and a visual identity that refuses both the Tableau dashboard it is today and the Workbench eval-tool it was tempted to become. Ink-cobalt over slate-blue. Operations-center over chat-box. Structured artifacts over bubbles. Preview-then-confirm over black-box optimism. Selective mono over mono-everywhere. Breathing over spinners. One confident accent, one considered type stack, one honest interaction model — and the discipline to ship them as a system before shipping anything on top.