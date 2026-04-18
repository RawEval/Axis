'use client';

import { useState } from 'react';
import { Check } from 'lucide-react';
import { Avatar, Badge, Button } from '@axis/design-system';
import { InviteModal } from '@/components/team/invite-modal';
import { useOrgStore } from '@/lib/org-store';
import { useMounted } from '@/lib/use-mounted';
import {
  ROLE_LABELS,
  canInvite,
  useOrgInvites,
  useOrgMembers,
  useOrgs,
  useRevokeInvite,
} from '@/lib/queries/orgs';

const ROLE_MATRIX: ReadonlyArray<{
  role: string;
  viewRuns: boolean;
  approveWrites: boolean;
  connectApps: boolean;
  manageTeam: boolean;
  manageBilling: boolean;
}> = [
  { role: 'Owner',   viewRuns: true, approveWrites: true,  connectApps: true,  manageTeam: true,  manageBilling: true },
  { role: 'Admin',   viewRuns: true, approveWrites: true,  connectApps: true,  manageTeam: true,  manageBilling: false },
  { role: 'Manager', viewRuns: true, approveWrites: true,  connectApps: true,  manageTeam: false, manageBilling: false },
  { role: 'Member',  viewRuns: true, approveWrites: false, connectApps: false, manageTeam: false, manageBilling: false },
  { role: 'Viewer',  viewRuns: true, approveWrites: false, connectApps: false, manageTeam: false, manageBilling: false },
];

const MATRIX_COLUMNS: ReadonlyArray<{ key: keyof (typeof ROLE_MATRIX)[number]; label: string }> = [
  { key: 'viewRuns', label: 'View runs' },
  { key: 'approveWrites', label: 'Approve writes' },
  { key: 'connectApps', label: 'Connect apps' },
  { key: 'manageTeam', label: 'Manage team' },
  { key: 'manageBilling', label: 'Manage billing' },
];

export default function TeamPage() {
  const mounted = useMounted();
  const { data: orgs } = useOrgs();
  const activeOrgId = useOrgStore((s) => s.activeOrg);

  // Resolve the active org from the store, falling back to the personal org.
  const resolvedOrg = mounted
    ? orgs?.find((o) => o.id === activeOrgId) ??
      orgs?.find((o) => o.is_personal) ??
      orgs?.[0]
    : undefined;

  const orgId = resolvedOrg?.id;
  const { data: members } = useOrgMembers(orgId);
  const { data: invites } = useOrgInvites(orgId);
  const revoke = useRevokeInvite(orgId);

  const [inviteOpen, setInviteOpen] = useState(false);
  const myRole = resolvedOrg?.role ?? 'viewer';
  const canInviteMembers = mounted && canInvite(myRole);

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="flex items-end justify-between gap-4">
        <div className="space-y-2">
          <h1 className="font-display text-display-l text-ink">
            {mounted && resolvedOrg ? `Team · ${resolvedOrg.name}` : 'Team'}
          </h1>
          <p className="text-body text-ink-secondary">
            People in this workspace and what they can do.
          </p>
        </div>
        {canInviteMembers && (
          <Button variant="secondary" size="sm" onClick={() => setInviteOpen(true)}>
            Invite
          </Button>
        )}
      </header>

      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Members · {members?.length ?? 0}
          </h2>
        </div>
        {!members || members.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-edge-subtle py-16">
            <p className="font-display text-heading-1 text-ink">Nobody here yet</p>
            <p className="text-body-s text-ink-tertiary">
              Invite a teammate to start collaborating.
            </p>
            {canInviteMembers && (
              <Button variant="primary" size="sm" onClick={() => setInviteOpen(true)}>
                Invite someone
              </Button>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-edge-subtle border-y border-edge-subtle">
            {members.map((m) => {
              const display = m.name?.trim() || m.email;
              return (
                <li key={m.user_id} className="flex items-center gap-4 px-2 py-3">
                  <Avatar name={display} size="md" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-body-s font-medium text-ink">
                      {display}
                    </div>
                    <div className="truncate text-caption text-ink-tertiary">
                      {m.email}
                    </div>
                  </div>
                  <Badge tone="neutral">{m.role.toUpperCase()}</Badge>
                  <span className="font-mono text-caption tabular-nums text-ink-tertiary">
                    Joined {new Date(m.joined_at).toLocaleDateString()}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {invites && invites.length > 0 && (
        <section className="space-y-4">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Pending invites · {invites.length}
          </h2>
          <ul className="divide-y divide-edge-subtle border-y border-edge-subtle">
            {invites.map((inv) => (
              <li key={inv.id} className="flex items-center gap-4 px-2 py-3">
                <Avatar name={inv.email} size="md" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-body-s text-ink">{inv.email}</div>
                  <div className="text-caption text-ink-tertiary">
                    Expires {new Date(inv.expires_at).toLocaleDateString()}
                  </div>
                </div>
                <Badge tone="warning">PENDING</Badge>
                <Badge tone="neutral">{ROLE_LABELS[inv.role].toUpperCase()}</Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => revoke.mutate(inv.id)}
                  disabled={revoke.isPending}
                >
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <details className="group rounded-lg border border-edge-subtle">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-body-s text-ink">
          <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Role matrix
          </span>
          <span className="text-caption text-ink-tertiary group-open:hidden">Show</span>
          <span className="hidden text-caption text-ink-tertiary group-open:inline">Hide</span>
        </summary>
        <div className="overflow-x-auto border-t border-edge-subtle px-4 py-4">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-edge-subtle">
                <th className="px-2 py-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
                  Role
                </th>
                {MATRIX_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className="px-2 py-2 text-center font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROLE_MATRIX.map((row) => (
                <tr key={row.role} className="border-b border-edge-subtle last:border-b-0">
                  <td className="px-2 py-2 font-mono text-mono-s uppercase tracking-[0.04em] text-ink">
                    {row.role}
                  </td>
                  {MATRIX_COLUMNS.map((col) => (
                    <td key={col.key} className="px-2 py-2 text-center">
                      {row[col.key] ? (
                        <Check
                          size={14}
                          className="mx-auto text-ink"
                          aria-label="Yes"
                        />
                      ) : (
                        <span className="text-ink-tertiary" aria-label="No">
                          —
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {orgId && (
        <InviteModal
          open={inviteOpen}
          onClose={() => setInviteOpen(false)}
          orgId={orgId}
          myRole={myRole}
        />
      )}
    </div>
  );
}
