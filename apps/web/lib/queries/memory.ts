'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type MemoryRow = {
  id: string;
  tier: 'episodic' | 'semantic' | 'procedural';
  type: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type MemoryStats = {
  user_id: string;
  episodic_count: number;
  semantic_count: number;
  embedding_provider: string;
};

export function useMemoryStats() {
  return useQuery<MemoryStats>({
    queryKey: ['memory', 'stats'],
    queryFn: () => api.get<MemoryStats>('/memory/stats'),
    staleTime: 30_000,
  });
}

export function useMemorySearch(query: string, tier: string | null) {
  return useQuery<MemoryRow[]>({
    queryKey: ['memory', 'search', query, tier ?? 'all'],
    queryFn: () =>
      api.post<MemoryRow[]>('/memory/search', {
        query,
        tier: tier && tier !== 'any' ? tier : null,
        limit: 50,
      }),
    staleTime: 15_000,
  });
}

export function useDeleteEpisodic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<{ ok: boolean; id: string }>(`/memory/episodic/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory'] });
    },
  });
}
