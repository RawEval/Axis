# ADR 010 — Organizations, roles, and delegation

**Date:** 2026-04-16
**Status:** Accepted
**Triggered by:** ADR 009 positioning pivot, the feature that Anthropic structurally won't ship.
**Supersedes:** `projects-model.md` (ADR 002) single-owner assumption. Projects now belong to organizations.

## Rule zero — roles are permission tiers, never job titles

This is the most important sentence in this doc:

> **A role describes what a person can do inside Axis. It never describes what they are in their company.**

We do not ship "President," "VP," "Director," "IC," "CEO," or any other job-title label anywhere in the product. The five role names are `owner`, `admin`, `manager`, `member`, `viewer`. They map to permission tiers. A 20-year-old first-week hire and a 55-year-old founder can both be "owner" of different organizations without any product surface suggesting otherwise. The product stays out of assumptions about hierarchy, seniority, or respect.

When an invite UI asks "what role should this person have," the options are the five above, with a plain-language description of what each permission tier allows. Never a dropdown of job titles.

## Model

```
  organizations (the team / workspace container)
       │
       │  1–N
       ▼
  organization_members (user ↔ org with a role)
       │
       │  references
       ▼
  projects (scoped workspace inside an org)
       │
       │  1–N
       ▼
  project_members (user ↔ project with a role scoped to this project)
       │
       │  references
       ▼
  connectors, agent_actions, feed, history (everything already project-scoped)
```

- A user can belong to many orgs.
- Every org has at least one `owner`. Deleting the last owner is forbidden.
- Roles at the org level are the default for every project in that org.
- A user can be granted a *different* role at the project level, which overrides the org default for that one project.
- Projects can also have non-org members (a contractor you trust with one client project, nothing else). The contractor's access is scoped to exactly that project.

## The five roles

```
 ┌─────────┐   can do everything, including delete the org
 │  owner  │
 └────┬────┘
      │   invites
      ▼
 ┌─────────┐   manage members + projects + billing
 │  admin  │   cannot delete the org
 └────┬────┘
      │   invites
      ▼
 ┌─────────┐   manage projects they belong to + connectors + writes
 │ manager │
 └────┬────┘
      │   invites
      ▼
 ┌─────────┐   run reads + propose writes (gated by a manager+)
 │ member  │
 └────┬────┘
      │   (viewers cannot invite)
      ▼
 ┌─────────┐   read-only access to feed + history for granted projects
 │ viewer  │
 └─────────┘
```

Capability matrix:

| Capability | owner | admin | manager | member | viewer |
|---|---|---|---|---|---|
| Run agent reads | ✓ | ✓ | ✓ | ✓ | ✓ |
| Run agent writes (with gate) | ✓ | ✓ | ✓ | ✓ | ✗ |
| Run agent writes (auto-confirm low-risk) | ✓ | ✓ | ✓ | ✗ | ✗ |
| Connect a new tool | ✓ | ✓ | ✓ | ✗ | ✗ |
| Disconnect a tool | ✓ | ✓ | ✓ | ✗ | ✗ |
| Create a project | ✓ | ✓ | ✓ | ✗ | ✗ |
| Invite a member at-or-below own role | ✓ | ✓ | ✓ | ✗ | ✗ |
| Change someone's role | ✓ | ✓ (not owners) | ✗ | ✗ | ✗ |
| Remove a member | ✓ | ✓ (not owners) | ✗ | ✗ | ✗ |
| Manage billing | ✓ | ✓ | ✗ | ✗ | ✗ |
| Delete the org | ✓ | ✗ | ✗ | ✗ | ✗ |

**Monotonic invite rule:** a member at role X can only invite others at role X or lower. Nobody can invite above themselves. This is the one-line safety rail that prevents privilege escalation.

## Visual model — graph, not list

The members page in the web UI renders the org as a **graph**, not a table. Each node is a member. Each edge is an invite (who added whom). This is the mental model the product optimizes for: *"who gave access to whom, and can I trace the chain."*

```
        [org node: Acme Team]
               │
               │
       ┌───────┼───────────────┐
       │       │               │
  [owner:A] [owner:B]     [admin:C]
               │               │
        ┌──────┴───────┐    ┌──┴────┐
        │              │    │       │
   [manager:D]   [manager:E] [manager:F]
        │              │        │
    [member:G]    [member:H] [viewer:I]
```

Each node shows: the member's display name (never a job title), their role badge, the projects they have access to, and — on hover — who invited them and when. Clicking a node opens a side panel: full audit of that member's grants, sessions, and write actions.

The graph is deliberately *flat* when an org is small (< 5 members) — no fake hierarchy. Edges only appear once delegation actually happens.

## Project membership

Every project belongs to exactly one org. The project's member list is a **subset** of the org's member list, with potentially different roles:

```
Org: Acme Team
  members: [owner A, owner B, admin C, manager D, manager E, manager F, member G, member H, viewer I]

Project: Alpha engagement
  members: [manager D as manager, member G as member]
  default for others: no access

Project: Internal ops
  members: [owner A as owner, admin C as admin, manager D as member, manager E as manager]
  note: manager D is a manager in the org but only a member in this project
```

Access resolution (on every request):

```
def effective_role(user_id, project_id) -> Role | None:
    pm = project_members.lookup(user_id, project_id)
    if pm:
        return pm.role               # project override wins
    p = projects.get(project_id)
    om = organization_members.lookup(user_id, p.org_id)
    if om and p.default_grant == 'org':
        return om.role               # fall back to org role
    return None                      # no access
```

`projects.default_grant` is one of:
- `org` — every org member inherits their org role on this project (default for `Internal ops`-style projects)
- `explicit` — only members listed in `project_members` have access (default for `Client Alpha`-style projects, for isolation)

## Connector visibility rules

Connectors live at the project level (unchanged from ADR 002). The new rule: **who can use a connected tool in an agent run** is gated by role.

| Action on connector | owner | admin | manager | member | viewer |
|---|---|---|---|---|---|
| See it exists | ✓ | ✓ | ✓ | ✓ | ✓ |
| Read via the agent | ✓ | ✓ | ✓ | ✓ | ✓ |
| Propose a write (gated) | ✓ | ✓ | ✓ | ✓ | ✗ |
| Approve & execute a write | ✓ | ✓ | ✓ | ✗ | ✗ |
| Connect a new one | ✓ | ✓ | ✓ | ✗ | ✗ |
| Disconnect | ✓ | ✓ | ✓ | ✗ | ✗ |

The manager-approval-for-member-writes pattern means: members can propose a write, the system emits a `permission.request` event, a manager+ sees it in their inbox and approves/denies. This handles the "new hire can draft the email but a manager has to hit send" case without giving the new hire the literal scope to send.

## Token ownership — personal vs shared

A connector's OAuth token can be:

- **Personal** — a specific user's Gmail. Only that user can use it. If they leave the org, the token is revoked.
- **Shared** — a bot-installed Slack workspace. Tied to the org, not to one user. Persists even if the installer leaves.

Schema: `connectors.token_owner_user_id` (nullable). NULL means "shared, org-scoped."

The UI distinguishes: "Gmail (as sarah@acme.com — personal)" vs "Slack (#acme-workspace — shared)".

## Invites

The invite flow:

1. An owner/admin/manager opens the Members page and clicks "Invite."
2. Modal: email, role (at-or-below own role), optional project scope, optional note.
3. Backend creates a row in `organization_invites` with a random 32-char token, expires in 7 days.
4. (Phase 2) notification-service sends an email with a magic link `https://app.axis/accept-invite/<token>`.
5. (Phase 1) the modal shows a copyable link immediately — owner copies it into Slack DM or iMessage.
6. Invitee clicks the link:
   - If no Axis account → redirected to `/signup?invite=<token>` — signup flow creates an account and auto-accepts the invite.
   - If Axis account → `/accept-invite/<token>` — one-click accept, lands in the org.
7. Accept creates a row in `organization_members` with the invited role, and (if scoped) a row in `project_members` too.
8. Original invite row is marked consumed.

Invites are **user-verified** (the magic link is sent to the email the inviter typed). If the invitee uses a different email on signup, the invite cannot be claimed. This is deliberately strict.

## Audit

Every access-related event is logged in `permission_events` (already exists from ADR 006):

- `invite.created`, `invite.accepted`, `invite.expired`, `invite.revoked`
- `role.changed`, `role.revoked`
- `project_member.added`, `project_member.removed`, `project_member.role_changed`
- `connector.connected`, `connector.disconnected`
- `write.proposed`, `write.approved`, `write.denied`, `write.executed`, `write.rolled_back`

Owners/admins can export the audit log for any time window. Required for SOC 2.

## Personal orgs (backward-compat)

Every existing user already has a default "Personal" project (ADR 002 migration 005). Migration 007 creates a **personal org** for every existing user, sets them as the owner, and moves their default project under it.

From the user's point of view nothing changes until they invite a second person — at which point the "Personal" org becomes "their team" and the delegation model kicks in.

New signups also get a personal org created in the same atomic transaction as the user + default project (currently auth-service does this for the project; it'll add the org row).

## Not in scope for this ADR

- **SSO / SAML** — Phase 3 enterprise feature. Will plug into `organization_members` as `identity_provider_sub` columns.
- **SCIM** — same tier.
- **Per-role custom permissions** (Linear-style fine-grained) — we ship the 5 fixed tiers and see if users actually want more.
- **Guest users** — for cross-company projects. Phase 2.
- **Cross-org resource sharing** — intentionally unsupported. Each org is an isolation boundary.

## Open questions

- **What is the minimum viable invite UX for Phase 1 without email delivery?** Copy-link-to-clipboard modal (chosen). When notification-service gets real SMTP, we flip a flag and emails go out.
- **Can a user leave their own org?** Only if they're not the last owner. Otherwise transferring ownership is required.
- **What happens to agent_actions when a member is removed?** The rows stay (audit trail) but become read-only for anyone except owners+admins.
- **Role-change notifications to the affected user?** Yes, they land in their activity feed as an `axis` event.

## References

- `projects-model.md` — ADR 002, single-owner assumption that this ADR supersedes
- `permissions-model.md` — ADR 006, Claude-Code-style per-capability grants (orthogonal — these are grants *within* a role, this ADR is the role layer)
- `byo-credentials.md` — ADR 003, per-user BYO OAuth apps (personal tokens, org-agnostic)
- `009-positioning-pivot.md` — ADR 009, why this matters for the product
- `../pitch/one-pager.md` — the external framing
