# Axis — Competitive Landscape & Integration Analysis

**Date:** 2026-04-18
**Scope:** Every company operating in the AI workspace agent / cross-tool AI assistant space
**Purpose:** Side-by-side comparison of integrations, auth approach, capabilities, and where Axis wins

---

## Master Comparison Table

### Category 1: Direct Competitors (Cross-Tool AI Workspace Platforms)

| Company | Integrations | Auth Flow | Read/Write | Proactive Layer | LLMs | Target Market | Pricing | Differentiator |
|---|---|---|---|---|---|---|---|---|
| **Axis (us)** | 5 (Slack, Notion, Gmail, Drive, GitHub) + Activity + Memory | OAuth popup + BYO credentials (project→org→user→default) | Read + Write (gated with diff preview + rollback) | Yes — webhook + poll ingestion, unanswered-message detector, relevance engine | Claude Sonnet 4.5 + Haiku 4.5 (configurable) | Startups on Slack+Notion+Linear stack | Not yet priced (pre-seed) | BYO OAuth + write diff/rollback + proactive + per-action eval + org RBAC with delegation |
| **Dust.tt** (YC W23) | 5+ (Slack, Drive, Notion, Confluence, GitHub) + 200 MCP actions | OAuth popup, admin-managed | Read + Write (200+ actions via MCP) | No proactive monitoring | Model-agnostic (Claude, GPT, Gemini, Mistral) | Mid-market to enterprise (5,000+ orgs) | EUR 29/user/month (Pro), Enterprise custom | No-code agent builder, model choice, SOC 2 Type II |
| **Glean** | 100+ connectors | Admin-managed OAuth/API keys, enterprise SSO | Primarily read; write via Agents (secondary) | Partial — Glean Apps can trigger on events | Model Hub (OpenAI, Google, Anthropic, Meta) | Enterprise (Fortune 500), 100-seat minimum | ~$50/user/month, min ~$60K/year | Enterprise Graph, permission-aware retrieval, best-in-class search |
| **Anthropic Claude** (Connectors) | 50+ connectors | OAuth popup per connector | Mostly read, some interactive writes | None — entirely reactive | Claude only | Individual to enterprise | Pro $20/mo, Team $25/user/mo | Best-in-class LLM reasoning, native MCP |
| **Dashworks AI** | Multiple knowledge bases, docs, tickets | Admin-managed connectors | Read-only (search + Q&A) | No | Not disclosed | Mid-market to enterprise | Not public | Lightweight enterprise knowledge search, Glean alternative |
| **Lindy AI** | 5,000+ via Pipedream Connect | OAuth managed by platform | Read + Write (CRM, email, calendar, phone calls) | Partial — proactive scheduling | Multi-model | SMB to mid-market | Free tier, paid ~$49/mo | "AI employees", voice agents, computer use |

### Category 2: Platform-Native AI (Walled Gardens)

| Company | Integrations | Auth Flow | Read/Write | Proactive | LLMs | Target | Pricing | Differentiator |
|---|---|---|---|---|---|---|---|---|
| **Microsoft Copilot** (M365) | Word, Excel, PPT, Outlook, Teams, SharePoint + 1,400 MCP connectors | Microsoft Entra ID (native SSO) | Full read + write | Yes — Work IQ proactive insights | OpenAI GPT (exclusive) | Enterprise (M365 customers) | $30/user/month add-on | Deepest M365 integration, Graph-level data |
| **Google Gemini** (Workspace) | Gmail, Docs, Sheets, Slides, Meet, Calendar, Drive + Studio connectors | Google account native | Full read + write within Google | Limited — smart suggestions | Gemini 3 Pro (exclusive) | Google Workspace customers | Bundled in plans ($8.40-$26.40/user/mo) | Native to Google, no separate AI cost |
| **Slack AI** (Salesforce) | Slack-only | Native (part of subscription) | Read-only (summarize, search) | Yes — daily channel recaps | Not disclosed | Any Slack customer | Included in Pro ($7.25-$8.75/user/mo) | Zero-setup AI inside existing tool |
| **Notion AI** | Notion-native + 70+ connected apps (Slack, Teams, GitHub) | Native + OAuth in admin settings | Full read + write within Notion | Limited — agents triggered, no background monitoring | Multi-model (GPT-5.2, Claude Opus 4.5, Gemini 3) | Notion-centric teams | Business $20-$24/user/mo (includes AI) | Autonomous agents inside Notion, multi-model |
| **Atlassian Rovo** | Jira, Confluence, JSM + MCP (GitHub, Figma, HubSpot, Box) | Atlassian Cloud SSO + MCP | Read + Write (ticket automation, reports) | Yes — service agents for ticket routing | Not disclosed | Atlassian customers | Bundled in Premium/Enterprise | Teamwork Graph, Rovo Studio, Deep Research |
| **Asana Intelligence** | Asana-native + Slack, Teams, Google, Jira, Salesforce | Native + OAuth | Read + Write within Asana | Yes — workload balancing | Not disclosed | Enterprise PM teams | Included in Business+ ($24.99/user/mo) | Workload balancing and capacity analysis |
| **ClickUp AI** | ClickUp-native + 1,000+ integrations | Native | Read + Write ("AI teammates") | Limited proactive | Proprietary (ClickUp Brain) | SMB to enterprise | ~$5-9/user/mo add-on | "Human-level AI teammates" assigned tasks |
| **Monday.com AI** | Monday-native | Native | Read + Write | Automated workflow triggers | Not disclosed | SMB to enterprise | $8/user/mo add-on | Visual workflow-focused AI |

### Category 3: Workflow Automation + AI Agents

| Company | Integrations | Auth | R/W | Proactive | LLMs | Target | Pricing | Differentiator |
|---|---|---|---|---|---|---|---|---|
| **Zapier** (Agents) | 9,000+ apps | OAuth per app | R+W | Trigger-based | Multi-model + MCP | SMB to enterprise | Free (400 activities), Pro $33/mo | Largest integration ecosystem |
| **n8n** | 500+ | OAuth/API key per node | R+W | Trigger-based | Multi-model (OpenAI, HuggingFace, Cohere, Gemini) | Technical teams | Free (self-hosted), Cloud EUR 24-800/mo | Open-source, self-hosted, human-in-loop |
| **Make.com** | Hundreds | OAuth per app | R+W | Trigger-based | AI modules | Non-technical SMB | From $10.59/mo | Visual scenario builder, affordable |
| **Bardeen AI** | Browser + app integrations | Browser extension + OAuth | R+W | Limited | AI playbook builder | Sales teams, recruiters | $129/mo starter | Browser automation + app automation |
| **Relay.app** | Growing set | OAuth | R+W | Trigger-based | BYOK for AI models | SMB | Free (5K credits), Pro $37/mo | Best human-in-loop controls, incognito mode |
| **Activepieces** | 300+ (all as MCP) | OAuth/API key | R+W | Trigger-based | Multi-agent chaining | Technical SMB | Free (unlimited), MIT license | Fully open-source, MCP-native |
| **Tray.ai** | 400+ + universal connector | OAuth + custom | R+W | Event-driven | Merlin Agent Builder | Enterprise | Pro ~$595/mo, Enterprise custom | Enterprise iPaaS + AI agent builder |
| **Workato** | Unlimited connectors | OAuth + enterprise SSO | R+W | Event-driven + Agentic Orchestration | Proprietary | Enterprise | $833-$15K/mo | Unlimited model (no per-connection caps) |

### Category 4: Meeting AI

| Company | Integrations | R/W | Proactive | Target | Pricing | Differentiator |
|---|---|---|---|---|---|---|
| **Otter.ai** | Zoom, Teams, Meet, Calendar, Slack | Read (transcribe) | Auto-joins meetings | SMB to enterprise | Free (300 min), Pro $16.99/mo | Real-time transcription + AI chat |
| **Fireflies.ai** | Zoom, Teams, Meet, Salesforce, HubSpot, Slack | Read + limited write (CRM push) | Auto-joins meetings | SMB to enterprise | Free, Pro $18/user/mo | 100+ languages, AskFred, CRM auto-pop |
| **Sembly AI** | Zoom, Teams, Meet, Webex, Slack, Asana, Jira | Read | Auto-joins meetings | SMB to mid-market | Free, Pro $10/mo | Team dashboards tracking topics |

### Category 5: Scheduling AI

| Company | Integrations | R/W | Proactive | Target | Pricing | Differentiator |
|---|---|---|---|---|---|---|
| **Reclaim.ai** | Google Cal, Outlook, Slack, Todoist, Asana, Jira, Linear | R+W (calendar) | Yes — defends focus time | Individual to team | Free, Starter $8/user/mo | Smart scheduling, habits, no-meeting days |
| **Clockwise** | — | — | — | — | **SHUT DOWN** | No longer operating |

### Category 6: Knowledge Management

| Company | Integrations | R/W | Proactive | Target | Pricing | Differentiator |
|---|---|---|---|---|---|---|
| **Guru** | 100+ (Slack, Teams, Salesforce, Zendesk, Confluence, Drive) | Read primarily | Content verification cycles | SMB to enterprise | ~$10/user/mo starter | Knowledge verification governance, MCP |

### Category 7: Emerging Startups

| Company | Focus | Stage | Notable Because |
|---|---|---|---|
| **Arahi AI** | Proactive personal assistant (inbox/calendar/tasks) | Early | Most conceptually similar to Axis's proactive layer |
| **Tasklet** (YC) | AI agent connecting every tool via integrations/MCP | Early | YC-backed cross-tool agent |
| **Pentagon** | Workspace for AI employees to communicate and coordinate | Early | Multi-agent workspace |
| **Instruct** | Build autonomous agents with plain English | Early | Natural-language agent builder |
| **Sintra AI** | Team of specialized AI "Helpers" | Early | SMB-focused AI employees |
| **Adept AI** | ACT-1 model learns to use software by observation | Early | Works with any UI without APIs |
| **Orby AI** | Large Action Model for cross-department workflows | Early | Proprietary action model |
| **eesel AI** | AI for helpdesk/knowledge base | Growth | Flat-rate pricing |
| **Komo AI** | Agentic AI for centralized operations | Growth | Enterprise ops focus |

---

## Axis Integration Capacity Assessment

### Current integrations (13 capabilities)

| App | Confidence (0-100) | Why This Score | Read Capabilities | Write Capabilities |
|---|---|---|---|---|
| **Slack** | **95** | Deepest integration of any connector. 6 capabilities (search, channel summary, thread context, user profile, post, react). Events API webhook ingestion. Proactive unanswered-message detector. The highest-value tool for startup teams — where real-time decisions happen. | search, channel_summary, thread_context, user_profile | post (gated), react (gated) |
| **Notion** | **85** | Strong search + write-back with diff preview + snapshot rollback. Background poll ingestion every 15min. Critical for document-heavy teams. Missing: database writes, page creation, block editing. | search, blocks (for snapshot) | append (gated, with diff preview + rollback) |
| **Gmail** | **70** | Search works well. Send is gated (ALWAYS). Missing: draft creation, label management, Pub/Sub push for real-time ingestion (needs GCP infra). Every team uses email but usage is declining in favor of Slack/Teams. | search (messages.list + metadata get) | send (gated, ALWAYS) |
| **Google Drive** | **65** | File search with Drive query syntax works. Missing: file content read (Doc/Sheet body), file creation, edit, shared drive support. Drive is the file layer — important but secondary to messaging. | search (files.list) | — (Phase 2) |
| **GitHub** | **70** | Issue/PR search works. Missing: repo file read, commit history, PR review comments, issue creation, webhook ingestion. Critical for engineering-heavy teams. | search (issues + PRs) | create_issue_comment (client exists, not yet a capability) |
| **Linear** | **40** | Schema ready (migration 006). No OAuth, no client, no capability. Many startup teams use Linear over Jira. Should be next connector to build. | — | — |
| **Google Calendar** | **35** | Not started. Google OAuth is shared with Gmail/Drive. High value for scheduling context ("what's on my calendar today"). | — | — |
| **Jira** | **30** | Phase 2 per spec. Large enterprise tool but Axis targets startups who prefer Linear. | — | — |
| **Confluence** | **25** | Phase 2. Enterprise wiki — less relevant for startups on Notion. | — | — |
| **Microsoft Teams** | **20** | Phase 2. Axis targets the Slack+Notion stack, not Microsoft. Would need a separate Microsoft Graph OAuth flow. | — | — |
| **Figma** | **35** | Design-heavy teams need this. API is REST-based, OAuth straightforward. High value for product teams. | — | — |
| **Airtable** | **25** | Phase 2 per spec. Some startups use it as a lightweight DB. | — | — |
| **HubSpot/Salesforce** | **30** | CRM integration. Important for sales-focused startups. Not core to the Slack+Notion+GitHub stack. | — | — |

### Integration priority matrix (what to build next)

| Priority | App | Effort | Impact | Why |
|---|---|---|---|---|
| **1** | **Linear** | 1 day | High | Most startups on the Axis target stack use Linear. Proven OAuth pattern. |
| **2** | **Google Calendar** | 0.5 day | High | Shares Google OAuth. "What's on my calendar" is a daily query. |
| **3** | **GitHub (deeper)** | 1 day | High | Add webhook ingestion, PR review, file read. Engineering teams need depth. |
| **4** | **Notion (deeper)** | 1 day | Medium | Database writes, page creation, block editing. Power users need it. |
| **5** | **Figma** | 1 day | Medium | Design teams. File inspection, comment read. |
| **6** | **Gmail Pub/Sub** | 1 day | Medium | Real-time email ingestion. Needs GCP project. |
| **7** | **Jira** | 1 day | Low (for startups) | Enterprise fallback for teams not on Linear. |

---

## How They Handle Integration (Auth Flow Comparison)

| Approach | Who Uses It | User Experience | Axis Advantage |
|---|---|---|---|
| **OAuth popup (platform-owned app)** | Dust, Claude, Zapier, Axis, Lindy | Click Connect → popup → Allow → done. User never sees Client ID. | Same UX. Axis adds BYO credentials on top for compliance. |
| **Admin-managed connectors** | Glean, Moveworks, Workato, Tray | IT admin configures in a dashboard. End users don't connect individually. | Axis supports both: user self-service Connect + admin BYO credentials. |
| **Native (built into the platform)** | M365 Copilot, Google Gemini, Slack AI, Notion AI | Zero-click. AI is just "there" in the tool you already use. | Axis can't match this — but these are walled gardens. Axis is the cross-tool layer. |
| **API key paste** | n8n, Activepieces (for AI models) | Paste a key into a config field. Developer-friendly but not consumer-friendly. | Axis never exposes API keys to end users. |
| **BYO OAuth credentials** | **Only Axis** | Enterprise admin registers their own OAuth app for compliance, then every team member uses it. Project→org→user→default resolution. | Unique in the market. Zero competitors offer this. |

---

## Where Axis Wins (Unique Competitive Advantages)

| Feature | Axis | Closest Competitor | Gap |
|---|---|---|---|
| **BYO OAuth credentials** | Yes — multi-scope resolution (project→org→user→default) | Nobody | Completely unaddressed in the market |
| **Write diff preview + 30-day rollback** | Yes — DiffViewer → confirm → execute → snapshot | Nobody | No competitor shows a diff before executing writes |
| **Per-action LLM-as-judge eval** | Yes — Haiku scores every run on 3 dimensions | Nobody | No competitor evaluates every agent action with a judge model |
| **Correction → behavior mutation loop** | Yes — short-loop delta prepended to system prompt | Nobody | No competitor closes the correction feedback loop this tightly |
| **Proactive + cross-tool + write-safe** | Yes — all three together | Partial: Glean (proactive + read), Dust (cross-tool + write) | Nobody combines all three |
| **Three-tier memory** | Yes — Qdrant episodic + Neo4j semantic + Postgres procedural | Glean (Enterprise Graph), Notion AI (knowledge graph) | Nobody exposes memory as a user-inspectable + editable tier |
| **Startup tool stack focus** | Slack + Notion + Gmail + Drive + GitHub + Linear | Dust (closest) | Dust targets mid-market; Axis targets pre-seed to Series A |

---

## Biggest Threats to Watch

| Threat | Risk Level | Timeframe | Mitigation |
|---|---|---|---|
| **Claude Connectors adding proactive features** | High | 6-12 months | Ship proactive layer deeper — surface patterns, not just events |
| **Dust.tt adding proactive monitoring** | High | 3-6 months | They have the infra; Axis needs to ship the proactive moat first |
| **Notion AI expanding beyond Notion** | Medium | 6-12 months | Already multi-model + agents; could become a workspace layer |
| **Glean launching a startup tier** | Medium | 12+ months | Glean's DNA is enterprise; unlikely to go below $50/user/mo |
| **Arahi AI** | Low-Medium | 12+ months | Early stage but conceptually similar proactive approach |
| **Zapier Agents getting smarter** | Medium | 6 months | 9,000 integrations is unbeatable; but Zapier is automation, not workspace intelligence |

---

## Summary

**37 companies** analyzed across 7 categories. Axis's positioning — proactive cross-tool workspace layer for startups with BYO credentials, write safety (diff+rollback), per-action eval, and a correction-driven behavior loop — is **unique in the market**. No single competitor combines all five pillars.

The closest competitor is **Dust.tt** (cross-tool + write + model-agnostic) but they lack proactive monitoring, BYO OAuth, write safety, and eval. The biggest threat is **Anthropic Claude** adding proactive features to their Connectors product, which would commoditize Axis's read layer.

**Recommended immediate action:** Ship Linear integration (1 day) + Google Calendar (0.5 day) to complete the startup tool stack before Dust or Claude fill that gap.
