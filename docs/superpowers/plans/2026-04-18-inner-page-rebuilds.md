# Axis UI Plan 6 — Inner-Page Rebuilds (Activity, History, Memory, Settings, Team, Projects, Connections)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild seven inner-app pages (`/feed`, `/history`, `/memory`, `/settings`, `/team`, `/projects`, `/connections`) per the artifact (§3d-§3k), so the whole app shows the new design language end-to-end — not just the auth + Home + Chat pages we already shipped.

**Architecture:** Each task takes one page, reads the existing implementation, identifies the React Query / mutation hooks + state to preserve, and reshapes the JSX to use the design-system primitives built in Plans 1-5. No new design-system primitives in this plan — every component already exists. No backend changes; pages consume the same API surface.

**Tech Stack:** Existing — no new deps.

**Spec:** `docs/superpowers/specs/2026-04-18-workbench-style-ui-redesign.md` and `docs/compass_artifact_wf-99c65767-b8eb-4aa5-b2a0-64ee6a758ac2_text_markdown.md` (§3d Activity, §3e History, §3f Connections, §3h Memory, §3i Settings, §3j Team, §3k Projects).

**Out of scope** (handed off):
- Plan 7: PermissionCard rebuild (per A1 amendment), LiveTaskTree v2 (artifact §4), Credentials migration into Connections RightPanel, Admin dashboard route (artifact §3l), backend support for capability tiers / undo handlers / audience counter / trust mode.
- Plan 8: Onboarding / demo workspace seed + Playwright visual regression.

**Available primitives in `@axis/design-system` after Plans 1-5:**
Button, Input, Card+slots, Badge, StatusBadge, Avatar, Kbd, Skeleton, SegmentedControl, Modal+slots, Toast (toast.success/error/info/warning/action + ToastViewport), DropdownMenu+children, Tooltip+TooltipProvider, Tabs+children, BreathingPulse, AgentStateDot, CitationChip, PromptInput, DiffViewer, WritePreviewCard.

**Working in apps/web:**
- `useRightPanel().open({ title, body })` opens the contextual RightPanel
- `toast.success/info/error/action` for global toasts (mounted in Shell)
- `useTheme()` for theme reads/sets

**Conventions for this plan:**
- Page heading: `<h1 className="font-display text-display-l text-ink">Title</h1>` per Home page convention.
- Section heading inside a page: `<h2 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">SECTION NAME</h2>` (the same SectionHeader pattern used on Home).
- Page outer wrapper: `<div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">` for everything except Activity/History which use a tighter `max-w-[860px]`.
- Empty state: centered, dashed-border box, faint icon (lucide), display heading, body subtitle, optional CTA.
- Hairline-bordered list rows with hover `bg-canvas-elevated`.
- Status pills via `<Badge>` or `<StatusBadge>`.

---

## File structure

**Modify:**

```
apps/web/app/(app)/feed/page.tsx           # Activity rebuild
apps/web/app/(app)/history/page.tsx        # History rebuild
apps/web/app/(app)/memory/page.tsx         # Memory rebuild
apps/web/app/(app)/settings/page.tsx       # Settings tabbed rebuild
apps/web/app/(app)/team/page.tsx           # Team table rebuild
apps/web/app/(app)/connections/page.tsx    # Connections canvas rebuild
apps/web/components/connections-content.tsx # Update inside Connections
```

**Create:**

```
apps/web/app/(app)/projects/page.tsx       # New — list view (existing /projects/new stays)
```

**Total:** 1 new file, 7 modified, 8 commits.

---

## Phase A — Per-page rebuilds

### Task A1: Activity page rebuild (`/feed`)

Per artifact §3d: two lanes (Proactive + Historical), reverse-chrono firehose, 56-px row pattern, time-divided list (Today / Yesterday / Earlier this week), filter chips at top. The current page already has these blocks; this task tightens the visual treatment and swaps in the new primitives.

**Files:** Modify `apps/web/app/(app)/feed/page.tsx`.

- [ ] **Step 1: Read the current page** (`cat apps/web/app/\(app\)/feed/page.tsx`).

- [ ] **Step 2: Identify what to preserve.** All existing query hooks (likely `useActivityFeed`, `useDismissSurface`, etc.), state, event-source colors. The page already has a "Needs your attention" + "Recent activity" structure — keep that conceptual split.

- [ ] **Step 3: Restructure to the new pattern.** Outer wrapper `<div className="mx-auto flex w-full max-w-[860px] flex-col gap-8 px-6 py-10">`. Replace the page header with:
   ```tsx
   <header className="space-y-2">
     <h1 className="font-display text-display-l text-ink">Activity</h1>
     <p className="text-body text-ink-secondary">Everything Axis has done — and everything that needs your attention.</p>
   </header>
   ```
   Replace section headers ("NEEDS YOUR ATTENTION", "RECENT ACTIVITY") with:
   ```tsx
   <h2 className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">Needs your attention</h2>
   ```
   Replace surface cards with `<Card>` from design-system; inside each card body use a flex row: 16-px lucide icon (faint, monochrome — DROP per-source brand colors per artifact §3f), bold body title, secondary excerpt, mono timestamp + `<Badge tone="…">` for signal type on the right. Confidence as `<Badge tone="warning">LOW</Badge>` / `MED` / `HIGH` instead of percentages.

   Replace event rows with hairline-bordered list rows using the same icon-monochrome pattern.

   Add a filter `<SegmentedControl>` at the top with options `all / approvals / writes / errors / proactive` if the existing page has filter UI; otherwise skip.

- [ ] **Step 4: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5 && pnpm --filter @axis/web build 2>&1 | tail -5
   ```
   ```bash
   git add apps/web/app/\(app\)/feed/page.tsx && git commit -m "feat(web): rebuild Activity page per artifact §3d"
   ```

### Task A2: History page rebuild (`/history`)

Per artifact §3e: search+filter table of past runs. Columns: title, project, duration, steps, status, when. Click → opens RightPanel with run detail (use `useRightPanel().open(...)`). Filter row at top.

**Files:** Modify `apps/web/app/(app)/history/page.tsx`.

- [ ] **Step 1: Read the current page.**

- [ ] **Step 2: Preserve `useHistoryQuery` (or whatever it's called) + URL search params.**

- [ ] **Step 3: New layout:**
   - Page heading: `<h1 className="font-display text-display-l text-ink">History</h1>`.
   - Search row: `<Input>` with leading icon + a `<SegmentedControl>` for status filter (`ALL / DONE / FAILED`).
   - Table: hairline divider rows. Each row:
     ```tsx
     <button
       type="button"
       onClick={() => useRightPanel.getState().open({ title: run.title, body: <RunDetailPanel runId={run.id} /> })}
       className="w-full flex items-center gap-4 px-4 py-3 border-b border-edge-subtle text-left hover:bg-canvas-elevated transition-colors"
     >
       <span className="font-mono text-mono-s text-ink-tertiary tabular-nums w-32">{formatTime(run.created_at)}</span>
       <span className="flex-1 text-body-s text-ink truncate">{run.prompt}</span>
       <Badge tone={run.status === 'done' ? 'success' : 'danger'} dot>{run.status}</Badge>
     </button>
     ```
   - Empty state when no runs: dashed-border centered card with the artifact §6 wording: title "No past runs", subtext "Your run history appears here once Axis starts working.", CTA `Start a run` linking to `/chat`.

- [ ] **Step 4: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/history/page.tsx && git commit -m "feat(web): rebuild History page per artifact §3e"
   ```

### Task A3: Memory page rebuild (`/memory`)

Per artifact §3h: three tiers (Pinned, Episodic, Semantic), each a collapsible section. Search + Add at top. Bulk clear modal.

**Files:** Modify `apps/web/app/(app)/memory/page.tsx`.

- [ ] **Step 1: Read the current page.**

- [ ] **Step 2: Preserve existing memory query + delete/pin mutations.**

- [ ] **Step 3: New layout:**
   - Page heading + brief description.
   - Top row: search `<Input>` + `<Button variant="primary" size="sm">+ Add memory</Button>` + ghost `Bulk clear…` link that opens a confirmation `<Modal>`.
   - Three `<section>` blocks. Each section header is the mono-uppercase pattern with a count: `PINNED · 12`. Each row is hairline-bordered, displays an icon (📌 lucide for pinned, ● for episodic, ◆ for semantic — use lucide `Pin`, `Circle`, `Diamond`), body text, and hover-revealed action buttons (Forget, Pin, Promote, View source).
   - Use `<Skeleton>` for loading state (3 rows per tier).

- [ ] **Step 4: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/memory/page.tsx && git commit -m "feat(web): rebuild Memory page with 3-tier collapsible sections per artifact §3h"
   ```

### Task A4: Settings page rebuild (`/settings`)

Per artifact §3i: tabbed (Account / Appearance / Capabilities / Output quality / Notifications / Advanced / Sign out). Use the design-system `<Tabs>` primitive built in Plan 2.

**Files:** Modify `apps/web/app/(app)/settings/page.tsx`.

- [ ] **Step 1: Read the current page.**

- [ ] **Step 2: Preserve account query, output-quality query, sign-out mutation.**

- [ ] **Step 3: New layout:**
   - Page heading: `<h1 className="font-display text-display-l text-ink">Settings</h1>`.
   - Tabbed with `<Tabs defaultValue="account">`:
     ```tsx
     <Tabs defaultValue="account">
       <TabsList>
         <TabsTrigger value="account">Account</TabsTrigger>
         <TabsTrigger value="appearance">Appearance</TabsTrigger>
         <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
         <TabsTrigger value="output">Output quality</TabsTrigger>
         <TabsTrigger value="notifications">Notifications</TabsTrigger>
         <TabsTrigger value="advanced">Advanced</TabsTrigger>
       </TabsList>

       <TabsContent value="account">
         {/* preserve the existing account fields, but use the new Field/Input pattern */}
       </TabsContent>

       <TabsContent value="appearance">
         <ThemeSection />        {/* SegmentedControl for theme: SYSTEM / LIGHT / DARK */}
         <DensitySection />      {/* SegmentedControl for density: COMFORTABLE / COMPACT */}
       </TabsContent>

       <TabsContent value="capabilities">
         <p className="text-body-s text-ink-tertiary">
           What Axis can do — capability scope tuner. Coming soon (Plan 7).
         </p>
       </TabsContent>

       <TabsContent value="output">
         {/* preserve the output-quality block */}
       </TabsContent>

       <TabsContent value="notifications">
         <p className="text-body-s text-ink-tertiary">Notification preferences. Coming soon.</p>
       </TabsContent>

       <TabsContent value="advanced">
         {/* preserve the sign-out button styled as a danger ghost link */}
       </TabsContent>
     </Tabs>
     ```
   - The Theme section uses `<SegmentedControl>` with `useTheme()`:
     ```tsx
     const { theme, setTheme } = useTheme();
     <SegmentedControl
       value={theme}
       onChange={setTheme}
       options={[
         { value: 'system', label: 'System' },
         { value: 'light',  label: 'Light'  },
         { value: 'dark',   label: 'Dark'   },
       ]}
     />
     ```
   - Sign-out is now under Advanced as `<button className="text-body-s text-danger hover:underline">Sign out</button>`.

- [ ] **Step 4: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/settings/page.tsx && git commit -m "feat(web): rebuild Settings as tabbed surface per artifact §3i"
   ```

### Task A5: Team page rebuild (`/team`)

Per artifact §3j: members table + role matrix (no org-chart). The existing org-chart graph (`MembersGraph`) was already removed in earlier work; this task builds the table + matrix.

**Files:** Modify `apps/web/app/(app)/team/page.tsx`.

- [ ] **Step 1: Read the current page.**

- [ ] **Step 2: Preserve `useTeamMembers`, `useInviteMember` mutations.**

- [ ] **Step 3: New layout:**
   - Page heading + ghost-secondary `Invite` button that opens an invite `<Modal>`.
   - Members table — hairline-bordered list:
     ```tsx
     <ul className="divide-y divide-edge-subtle border-y border-edge-subtle">
       {members.map((m) => (
         <li key={m.id} className="flex items-center gap-4 py-3 px-2">
           <Avatar name={m.name} size="md" />
           <div className="flex-1 min-w-0">
             <div className="text-body-s font-medium text-ink truncate">{m.name}</div>
             <div className="text-caption text-ink-tertiary truncate">{m.email}</div>
           </div>
           <Badge tone="neutral">{m.role.toUpperCase()}</Badge>
           <span className="text-caption text-ink-tertiary tabular-nums">{relativeTime(m.last_active)}</span>
         </li>
       ))}
     </ul>
     ```
   - Pending invites section below if any: same row pattern with `<Badge tone="warning">PENDING</Badge>` + ghost `Resend` / `Revoke` actions.
   - Role matrix (collapsed under a `<details>` or as the last section): a small table showing role × can-do columns. Mono uppercase role names. Five rows: Owner, Admin, Manager, Member, Viewer. Five columns: View runs, Approve writes, Connect apps, Manage team, Manage billing.

- [ ] **Step 4: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/team/page.tsx && git commit -m "feat(web): rebuild Team page with members table + role matrix per artifact §3j"
   ```

### Task A6: Projects list page (NEW — `/projects`)

Currently `/projects` 404s (only `/projects/new` exists). Per artifact §3k: searchable grid (3-column wide, 1-column narrow). Each project card: name, icon (monogram or emoji), description, connectors attached (Badge cluster), last-active. Click → switches project (no multi-project yet, so for V1 it links to project page placeholder).

**Files:**
- Create: `apps/web/app/(app)/projects/page.tsx`

- [ ] **Step 1: Check whether a `useProjects` hook exists** in `apps/web/lib/queries/`. If yes, use it. If not, the page renders an empty state.

   ```bash
   cd /Users/mrinalraj/Documents/Axis && ls apps/web/lib/queries/ 2>&1 | head
   ```

- [ ] **Step 2: Create the page:**
   ```tsx
   'use client';

   import Link from 'next/link';
   import { Plus, FolderOpen } from 'lucide-react';
   import { Button, Card, CardBody, Input } from '@axis/design-system';
   import { useState } from 'react';

   // If useProjects exists, import it. Otherwise this stub uses an empty array.
   const projects: ReadonlyArray<{ id: string; name: string; description: string; lastActive: string }> = [];

   export default function ProjectsPage() {
     const [query, setQuery] = useState('');
     const filtered = query
       ? projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
       : projects;

     return (
       <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-8 px-12 py-10">
         <header className="flex items-center justify-between">
           <h1 className="font-display text-display-l text-ink">Projects</h1>
           <Link
             href="/projects/new"
             className="inline-flex items-center gap-2 h-9 px-4 rounded-md bg-accent text-accent-on text-body-s font-medium hover:bg-accent-hover transition-colors"
           >
             <Plus size={14} aria-hidden="true" />
             New project
           </Link>
         </header>

         <Input
           placeholder="Search projects…"
           value={query}
           onChange={(e) => setQuery(e.target.value)}
         />

         {filtered.length === 0 ? (
           <div className="flex flex-col items-center justify-center gap-4 py-20 border border-dashed border-edge-subtle rounded-lg">
             <FolderOpen size={36} className="text-ink-tertiary" aria-hidden="true" />
             <div className="text-center space-y-1">
               <p className="font-display text-heading-1 text-ink">No projects yet</p>
               <p className="text-body-s text-ink-tertiary">Projects group related runs, memories, and connections.</p>
             </div>
             <Link
               href="/projects/new"
               className="inline-flex items-center gap-2 h-8 px-4 rounded-md bg-accent text-accent-on text-body-s font-medium hover:bg-accent-hover transition-colors"
             >
               <Plus size={14} aria-hidden="true" />
               New project
             </Link>
           </div>
         ) : (
           <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
             {filtered.map((p) => (
               <Card key={p.id} className="hover:border-edge-strong transition-colors">
                 <CardBody className="space-y-2">
                   <div className="text-body-l font-medium text-ink">{p.name}</div>
                   <div className="text-body-s text-ink-secondary">{p.description}</div>
                   <div className="text-caption text-ink-tertiary">{p.lastActive}</div>
                 </CardBody>
               </Card>
             ))}
           </div>
         )}
       </div>
     );
   }
   ```

   If `useProjects` exists, replace the const stub with the hook call and adapt the type. Otherwise the empty state is the only path — the LeftNav `/projects` link no longer 404s.

- [ ] **Step 3: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/projects/page.tsx && git commit -m "feat(web): add Projects list page per artifact §3k"
   ```

### Task A7: Connections page rebuild (`/connections`)

Per artifact §3f: a canvas view, NOT a settings list. For V1 we ship the same 3-column grid (already in place) but rebuild the cards per the new visual treatment — connector mark in monochrome, mono uppercase tool name, status pill, hover lift. The "canvas with hairline-tick connecting lines" treatment is deferred to a polish pass; the data + tile pattern lands now.

**Files:** Modify `apps/web/app/(app)/connections/page.tsx` and `apps/web/components/connections-content.tsx`.

- [ ] **Step 1: Read both files.**

- [ ] **Step 2: Preserve every existing handler** — OAuth popup detection, message listener, banner, `useConnectors` query, `connect.mutateAsync` / `disconnect.mutate`, the Suspense wrapper.

- [ ] **Step 3: Redesign the ToolCard component inside `connections-content.tsx`:**
   - Drop the per-source brand background (`bg-[#4A154B]` etc.) on the icon square. Replace with `bg-canvas-elevated text-ink`.
   - Tool name in mono uppercase: `<span className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink">{tool.label}</span>`.
   - Description on the next line as `text-body-s text-ink-secondary`.
   - Status as `<StatusBadge>` from design-system (`tone='running'` for connected, `tone='blocked'` for error, `tone='background'` for disconnected) OR `<Badge>` if simpler.
   - Card uses `<Card>` from design-system. Hover: `hover:border-edge-strong hover:shadow-e2 transition-all`.
   - Sync info inside connected state: hairline-bordered inner row with mono timestamp.
   - Buttons: Connect → `<Button variant="primary" size="sm">`. Disconnect → ghost.

- [ ] **Step 4: Update `connections/page.tsx` LoadingConnections** to use `<Skeleton>` from design-system instead of the hand-rolled `animate-pulse` div.

- [ ] **Step 5: Smoke + commit.**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm --filter @axis/web type-check 2>&1 | tail -5
   git add apps/web/app/\(app\)/connections/page.tsx apps/web/components/connections-content.tsx && git commit -m "feat(web): rebuild Connections page with monochrome connector tiles per artifact §3f"
   ```

---

## Phase B — Verify

### Task B1: Workspace verify

- [ ] **Step 1: Tests + type-check + lint + build:**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10
   pnpm --filter @axis/web type-check 2>&1 | tail -3
   pnpm --filter @axis/design-system type-check 2>&1 | tail -3
   pnpm lint 2>&1 | tail -5
   pnpm --filter @axis/web build 2>&1 | tail -10
   ```

   Expected: design-system **101** (unchanged — no primitive changes); web **31** (unchanged — pages don't ship new tests). All clean / green. The build route table should now show `/projects` as a static page in addition to the existing `/projects/new`.

- [ ] **Step 2: Manual dev smoke:**
   ```bash
   cd /Users/mrinalraj/Documents/Axis && rm -rf apps/web/.next && pnpm --filter @axis/web dev
   ```
   Visit each rebuilt route in dev:
   - `/feed` → Activity reads cleanly with mono section headers + monochrome icons.
   - `/history` → search + filter row, hairline rows, empty state if no runs.
   - `/memory` → 3 tiers visible with mono headers + counts.
   - `/settings` → tabs at top, click each to confirm content area swap. Theme tab uses SegmentedControl.
   - `/team` → members table with mono role pills, role matrix collapsed below.
   - `/projects` → new route, empty state with CTA → `/projects/new`.
   - `/connections` → tile grid with monochrome icons + mono labels.
   
   Stop dev when verified.

   (No commit for verify.)

---

## What we have at the end of this plan

- 7 inner-app pages rebuilt to artifact spec.
- `/projects` route exists (no longer 404 from LeftNav).
- Connector tiles drop per-tool brand colors per spec.
- Settings becomes tabbed per artifact §3i.
- Memory shows 3 tiers per artifact §3h.
- Team uses table + role matrix per artifact §3j (no org-chart).

## What we explicitly did NOT do (handed off)

- Plan 7: PermissionCard rebuild + LiveTaskTree v2 + Credentials migration into Connections RightPanel + Admin dashboard route + backend support for capability tiers, undo handlers, audience counter, trust mode.
- Plan 8: Onboarding/demo workspace seed + Playwright visual regression.

## Self-Review

- **Spec coverage:** Plan 6 covers artifact §3d-§3k for the 7 pages listed. The deferred items (§3g Credentials migration, §3l Admin) are explicitly called out + tied to Plan 7.
- **Placeholder scan:** No "TBD" / "implement later". Each task task says exactly what to preserve (existing hooks/mutations) and what to restructure (the JSX shell).
- **Type consistency:** No new types introduced. Each task uses primitives whose types were established in earlier plans. The Theme type used in Settings (`'system' | 'light' | 'dark'`) is consistent with `lib/theme.tsx`.
- **Commands:** Every `pnpm --filter` and `git add` path is correct.
