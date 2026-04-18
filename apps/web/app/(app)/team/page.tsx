'use client';

import { useState } from 'react';
import {
  Badge,
  Button,
  EmptyState,
  PageHeader,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui';
import { MembersGraph } from '@/components/team/members-graph';
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
    <div className="mx-auto flex min-h-full max-w-6xl flex-col gap-5 px-6 py-6">
      <PageHeader
        title={mounted ? `Team · ${resolvedOrg?.name ?? ''}` : 'Team'}
        actions={
          canInviteMembers && (
            <Button size="sm" onClick={() => setInviteOpen(true)}>
              Invite
            </Button>
          )
        }
      />

      <Panel>
        <PanelHeader>
          <div className="text-sm font-semibold text-ink">Members</div>
          <div className="text-xs text-ink-tertiary">
            {members?.length ?? 0} {members?.length === 1 ? 'person' : 'people'}
          </div>
        </PanelHeader>
        {!members || members.length === 0 ? (
          <EmptyState
            title="Nobody here yet"
            description="Invite a teammate to start collaborating."
            action={
              canInviteMembers && (
                <Button size="sm" onClick={() => setInviteOpen(true)}>
                  Invite someone
                </Button>
              )
            }
          />
        ) : (
          <PanelBody>
            <MembersGraph members={members} orgName={resolvedOrg?.name ?? 'Team'} />
          </PanelBody>
        )}
      </Panel>

      {invites && invites.length > 0 && (
        <Panel>
          <PanelHeader>
            <div className="text-sm font-semibold text-ink">Pending invites</div>
            <div className="text-xs text-ink-tertiary">{invites.length}</div>
          </PanelHeader>
          <PanelBody>
            <ul className="divide-y divide-edge-subtle">
              {invites.map((inv) => (
                <li key={inv.id} className="flex items-center justify-between py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-ink">{inv.email}</div>
                    <div className="text-xs text-ink-tertiary">
                      Expires {new Date(inv.expires_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{ROLE_LABELS[inv.role]}</Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => revoke.mutate(inv.id)}
                    >
                      Revoke
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </PanelBody>
        </Panel>
      )}

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
