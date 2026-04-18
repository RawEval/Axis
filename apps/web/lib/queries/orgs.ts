'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type Role = 'owner' | 'admin' | 'manager' | 'member' | 'viewer';

export type Organization = {
  id: string;
  name: string;
  slug: string | null;
  plan: 'free' | 'pro' | 'team' | 'enterprise';
  is_personal: boolean;
  role: Role;
  created_at: string;
};

export type Member = {
  user_id: string;
  email: string;
  name: string | null;
  role: Role;
  joined_at: string;
  invited_by: string | null;
};

export type Invite = {
  id: string;
  email: string;
  role: Role;
  project_id: string | null;
  token?: string | null;
  accept_url?: string;
  created_at: string;
  expires_at: string;
};

// ---------- Orgs ------------------------------------------------------------

export function useOrgs() {
  return useQuery<Organization[]>({
    queryKey: ['orgs'],
    queryFn: () => api.get<Organization[]>('/orgs'),
    staleTime: 60_000,
  });
}

export function useCreateOrg() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string }) => api.post<Organization>('/orgs', input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orgs'] }),
  });
}

// ---------- Members ---------------------------------------------------------

export function useOrgMembers(orgId: string | undefined) {
  return useQuery<Member[]>({
    queryKey: ['orgs', orgId, 'members'],
    queryFn: () => api.get<Member[]>(`/orgs/${orgId}/members`),
    enabled: Boolean(orgId),
    staleTime: 30_000,
  });
}

export function useChangeMemberRole(orgId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      api.patch<{ user_id: string; role: Role }>(
        `/orgs/${orgId}/members/${userId}`,
        { role },
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['orgs', orgId, 'members'] }),
  });
}

export function useRemoveMember(orgId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.delete<void>(`/orgs/${orgId}/members/${userId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['orgs', orgId, 'members'] }),
  });
}

// ---------- Invites ---------------------------------------------------------

export function useOrgInvites(orgId: string | undefined) {
  return useQuery<Invite[]>({
    queryKey: ['orgs', orgId, 'invites'],
    queryFn: () => api.get<Invite[]>(`/orgs/${orgId}/invites`),
    enabled: Boolean(orgId),
    staleTime: 10_000,
  });
}

export function useCreateInvite(orgId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      email: string;
      role: Role;
      project_id?: string;
      note?: string;
    }) => api.post<Invite>(`/orgs/${orgId}/invites`, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orgs', orgId, 'invites'] }),
  });
}

export function useRevokeInvite(orgId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) =>
      api.delete<void>(`/orgs/${orgId}/invites/${inviteId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orgs', orgId, 'invites'] }),
  });
}

// ---------- Role helpers ----------------------------------------------------

const RANK: Record<Role, number> = {
  owner: 0,
  admin: 1,
  manager: 2,
  member: 3,
  viewer: 4,
};

export function canInvite(inviterRole: Role): boolean {
  return inviterRole !== 'viewer';
}

export function canManageMembers(role: Role): boolean {
  return role === 'owner' || role === 'admin';
}

export function inviteableRoles(inviterRole: Role): Role[] {
  if (!canInvite(inviterRole)) return [];
  const minRank = RANK[inviterRole];
  return (Object.keys(RANK) as Role[]).filter((r) => RANK[r] >= minRank);
}

export const ROLE_LABELS: Record<Role, string> = {
  owner: 'Owner',
  admin: 'Admin',
  manager: 'Manager',
  member: 'Member',
  viewer: 'Viewer',
};

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  owner: 'Full control, including deleting the organization.',
  admin: 'Manage members, projects, and billing. Cannot delete the org.',
  manager: 'Manage projects they belong to, connectors, and writes.',
  member: 'Run reads, propose writes (gated by a manager or above).',
  viewer: 'Read-only access to feed and history for granted projects.',
};
