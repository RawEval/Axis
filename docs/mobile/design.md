# Mobile — iOS + Android design

**Status:** design · Phase 2 delivery
**Covers:** visual system, navigation, API contract, state, offline, notifications, screen-by-screen specs

This doc describes what the iOS and Android apps *should be*. The current repo has compiling skeletons at `apps/mobile-ios/` and `apps/mobile-android/` — enough to boot and ship a debug build, but not production-polished. This doc is the target for the Phase 2 mobile sprint.

## Design principles

1. **Match the web visually.** Same light theme, same slate + navy + single-blue accent palette, same typography rhythm. A user on the laptop at 9 AM should recognize the phone screen at 9:01 AM without a beat.
2. **Not a port — a companion.** The phone is for triage + action, not administration. Don't ship a Settings screen on mobile. Credentials live on the web. The mobile app shows what's happening and lets you do something about it.
3. **Consumption-first.** The hero surface is the proactive feed. Chat is secondary. Admin is absent.
4. **Offline-aware.** 48-hour activity cache locally per spec §8.2. The feed works on an airplane; writes queue until the connection returns.
5. **Rich notifications.** Inline accept/dismiss on proactive surfaces, straight from the push banner. No app-open required for the 80% case.
6. **Role-first, never role-seniority.** Every UI label we ship follows ADR 010 rule zero: owner / admin / manager / member / viewer, never job titles. On mobile the role badge is a small colored chip, same five strings as the web.

## Visual tokens (shared between iOS + Android)

```
Canvas        — #F7F8FA   (system bg, light)
Raised        — #FFFFFF   (cards, sheets)
Ink           — #0F172A   (body text)
Ink-secondary — #475569
Ink-tertiary  — #64748B
Edge          — #E2E8F0   (hairlines)
Brand         — #2563EB   (single accent, used sparingly)
Success       — #16A34A
Warning       — #D97706
Danger        — #DC2626
```

- Typography: system font (San Francisco on iOS, Roboto on Android). No custom font waterfalls on launch — costs precious milliseconds of time-to-interactive.
- Radius: 10pt for cards, 6pt for chips, 50% for avatars.
- Elevation: a single shadow tier — subtle (`0 1pt 2pt rgba(15,23,42,0.08)`). No Material-3 drama.
- Dark mode: implement day-one, mirror the tokens with the inverted slate palette.
- Haptics: medium impact on primary actions, light tick on list selection.

## Navigation

Four tabs. Same four as the web nav rail. No settings tab on mobile.

```
┌──────────────────────────────┐
│  ACTIVITY (default)          │  ← feed of proactive surfaces
├──────────────────────────────┤
│  ASK                         │  ← prompt box
├──────────────────────────────┤
│  HISTORY                     │  ← past agent actions
├──────────────────────────────┤
│  CONNECTIONS                 │  ← per-project connector status
└──────────────────────────────┘
```

Profile avatar in the top-right of every screen opens a sheet with: Org switcher, Project switcher, Sign out. Credentials and Memory are intentionally absent from mobile — the phone is for consumption and quick actions, not admin.

## Screens (iOS + Android, same structure)

### 1. Login

- Email + password
- Same visual language as the web login card
- "Sign in" primary button
- Biometric re-auth after first login (Face ID / Touch ID / fingerprint) if the user enables it in Settings on the web

### 2. Activity (default tab)

- Sectioned list:
  - **Pending proactive surfaces** (top)
  - **Today**
  - **Yesterday**
  - **Earlier this week**
- Each row: icon for the source (Slack/Notion/Gmail/GitHub/Linear), signal-type badge, title, context snippet, confidence dot, actions (Accept / Dismiss) as swipe-to-action
- Pull-to-refresh
- Inline agent action on tap: "Draft a reply" / "Summarize this thread" — pre-fills the Ask tab with a task-specific prompt

### 3. Ask

- Textarea at the bottom, results stream above
- Project picker at the top — one-tap to switch, same modal as the web but in a sheet
- Token delta streaming (Phase 2 streaming infra — `streaming-real-time.md`)
- Task tree renders inline as the agent progresses; tap any step to see its input/output

### 4. History

- Chronological list of past agent actions
- Each row: timestamp, first line of the prompt, tokens used, success/error badge
- Tap for full trace (prompt, plan, result, sources)
- Filter: by project, by status (all / flagged / corrected)
- Corrections from the inline "This was wrong" button feed the correction loop (spec §6.6)

### 5. Connections

- Per-project connector list (scoped to the active project)
- Each row: tool name, status, health dot, workspace name, last-sync timestamp
- Tap to expand → connect / disconnect button
- New-connector flow opens an in-app Safari / Chrome custom tab for OAuth (respects BYO credentials transparently — same logic as web)

### 6. Profile sheet (slide-up from the avatar button)

- Email + role badge
- Active org — tap to switch
- Active project — tap to switch
- Sign out
- Version string

*No Settings, no Credentials, no Memory, no Projects-CRUD, no Team management.* Those live on the web. This is a deliberate cut — the phone is for doing work, not configuring the workspace.

## API contract (same as web, shared `api.ts` equivalent)

```
GET    /healthz                         no auth — used to show "connected/offline"
POST   /auth/login                      → access_token
GET    /auth/me                         → current user
GET    /orgs                            → user's orgs
GET    /projects                        → user's projects (header: X-Axis-Project: active)
GET    /feed                            → proactive surfaces for active project
POST   /feed/{id}/accept                → accept surface
POST   /feed/{id}/dismiss               → dismiss surface
POST   /agent/run                       → run an agent task (long timeout)
GET    /agent/history                   → history for active project
GET    /connectors                      → per-project connector tiles
POST   /connectors/{tool}/connect       → open OAuth flow
DELETE /connectors/{tool}               → disconnect
```

Every request carries:
- `Authorization: Bearer <jwt>` from secure storage (iOS Keychain, Android EncryptedSharedPreferences)
- `X-Axis-Project: <uuid>` from the shared state store

## State management

- **iOS:** one `AxisStore` (ObservableObject) owning `user`, `org`, `project`, `feed`, `history`, `connectors`. Hydrated from Core Data for offline. `@Published` properties drive SwiftUI re-renders.
- **Android:** one `AxisViewModel` (Android `ViewModel` with `StateFlow`). Hydrated from Room for offline. Compose observes via `collectAsState()`.
- **Shared contract:** both apps consume the same types from `packages/kmm-shared` so they agree on `Project`, `Connector`, `Surface`, `AgentAction`. KMM business logic does the network + parsing; native UI renders.

## Offline

- Last 48 hours of `activity_events` cached locally (spec §8.2)
- Writes (proactive accept/dismiss, agent runs) queue with a retry token
- Queue is processed when `/healthz` returns 200
- User sees a muted "Offline — queuing" banner at the top of the screen; actions feel synchronous

## Notifications

- iOS: APNs via `notification-service` (Node / Fastify)
- Android: FCM via the same service
- Delivery pipeline: proactive-monitor → scores → notification-service → APNs/FCM
- Notification shapes:
  - **Proactive surface**: title + snippet + Accept/Dismiss inline buttons
  - **Permission request** (agent paused waiting for approval): title + "Approve" / "Deny" inline
  - **Write executed**: title + "Undo (30 days)" action
  - **Morning brief**: daily digest at the user's configured time

User-configurable per category in the web Settings page. Mobile never exposes the config surface.

## Security

- Tokens in secure storage only (Keychain / EncryptedSharedPreferences), never plain storage
- Biometric re-auth before any write action (configurable in web Settings)
- App-switcher screenshot blur: the OS screenshot of Axis when the user switches apps is blurred to hide sensitive content
- All network over HTTPS; certificate pinning in Phase 3

## What we ship in the Phase 1 skeleton (this commit)

- **iOS:** `apps/mobile-ios/` compiles via SwiftUI, 4 tabs, a minimal `AxisAPI` Swift client, no state management beyond local `@State`. Design tokens in code match the web.
- **Android:** `apps/mobile-android/` compiles via Gradle + Jetpack Compose, 4 tabs, a minimal Retrofit/Ktor client, no state management beyond local Compose state.
- **Both:** connect to `http://10.0.2.2:8000` (Android emulator) / `http://localhost:8000` (iOS simulator) and call `/healthz` + `/auth/login`.
- **Not shipped:** push notifications, offline cache, KMM shared types, biometric auth, dark mode. All Phase 2.

## Phase 2 sprint checklist

- Real KMM shared types from `packages/kmm-shared`
- Core Data / Room offline layer
- Real JWT storage in Keychain / EncryptedSharedPreferences
- SSE or polling for proactive surfaces (WebSocket is a Phase 3 upgrade)
- Push notification registration + delivery
- Dark mode
- Biometric re-auth
- Accessibility audit (VoiceOver / TalkBack)
- Localization scaffolding (English day-one, Hindi + Japanese Phase 3)
- App Store / Play Store privacy labels (spec §10 — all data encrypted in transit + at rest)

## What we explicitly do not build on mobile

- Settings / Credentials / Memory inspector / Projects CRUD / Team management — web only
- Complex multi-panel layouts — single-panel mobile UX
- Widgets — Phase 3
- Voice input — Phase 3
- iPad split view — Phase 3
