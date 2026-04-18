'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type ProactiveSurface = {
  id: string;
  signal_type: string;
  title: string;
  context_snippet: string | null;
  confidence_score: number | null;
  proposed_action: unknown;
  status: 'pending' | 'accepted' | 'dismissed';
  created_at: string;
};

export function useFeed() {
  return useQuery<ProactiveSurface[]>({
    queryKey: ['feed'],
    queryFn: () => api.get<ProactiveSurface[]>('/feed'),
    staleTime: 15_000,
  });
}

export function useSurfaceAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'accept' | 'dismiss' }) =>
      api.post<{ id: string; status: string }>(`/feed/${id}/${action}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['feed'] }),
  });
}
