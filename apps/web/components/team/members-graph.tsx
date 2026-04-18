'use client';

import clsx from 'clsx';
import { Badge } from '@/components/ui';
import { ROLE_LABELS, type Member, type Role } from '@/lib/queries/orgs';

/**
 * Members rendered as a visual graph, not a table.
 *
 * Roles are permission tiers (owner/admin/manager/member/viewer) — never
 * job titles (ADR 010 rule zero). The graph flattens when there's no
 * delegation depth yet, and grows tiers as delegation happens.
 *
 * Phase 1: deterministic tiered layout. Phase 2: interactive re-parenting
 * and side-panel audit log per node.
 */
export function MembersGraph({
  members,
  orgName,
}: {
  members: Member[];
  orgName: string;
}) {
  // Group members by role tier
  const tiers: { role: Role; members: Member[] }[] = (
    ['owner', 'admin', 'manager', 'member', 'viewer'] as Role[]
  )
    .map((role) => ({ role, members: members.filter((m) => m.role === role) }))
    .filter((tier) => tier.members.length > 0);

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <RootNode name={orgName} />

      {tiers.map(({ role, members: group }, idx) => (
        <div key={role} className="flex w-full flex-col items-center gap-2">
          <div className="h-6 w-px bg-edge" aria-hidden />
          <div className="flex flex-wrap items-center justify-center gap-3">
            {group.map((m) => (
              <MemberNode key={m.user_id} member={m} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RootNode({ name }: { name: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="rounded-md border border-edge-strong bg-canvas-subtle px-4 py-2 text-center">
        <div className="label-caps">Organization</div>
        <div className="mt-0.5 text-sm font-semibold text-ink">{name}</div>
      </div>
    </div>
  );
}

function MemberNode({ member }: { member: Member }) {
  const displayName =
    member.name?.trim() ||
    member.email.split('@')[0] ||
    'Member';

  return (
    <div
      className={clsx(
        'flex w-48 flex-col items-center rounded-md border bg-canvas-raised px-3 py-2 shadow-panel transition-colors',
        member.role === 'owner' ? 'border-brand-200' : 'border-edge',
      )}
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-edge-strong bg-canvas-subtle text-xs font-semibold text-ink-secondary">
        {displayName.charAt(0).toUpperCase()}
      </div>
      <div className="mt-1.5 w-full truncate text-center text-sm font-medium text-ink">
        {displayName}
      </div>
      <div className="truncate text-[11px] text-ink-tertiary">{member.email}</div>
      <div className="mt-1.5">
        <Badge tone={member.role === 'owner' ? 'brand' : 'neutral'}>
          {ROLE_LABELS[member.role]}
        </Badge>
      </div>
    </div>
  );
}
