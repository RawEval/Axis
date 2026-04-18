'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type Project = {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => api.get<Project[]>('/projects'),
    staleTime: 60_000,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; description?: string }) =>
      api.post<Project>('/projects', input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useRenameProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name, description }: { id: string; name: string; description?: string }) =>
      api.patch<Project>(`/projects/${id}`, { name, description }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/projects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useSetDefaultProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Project>(`/projects/${id}/set-default`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}
