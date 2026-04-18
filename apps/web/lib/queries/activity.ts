'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export type ActivityEvent = {
  id: string;
  source: string;
  event_type: string;
  actor: string | null;
  actor_id: string | null;
  title: string;
  snippet: string | null;
  raw_ref: Record<string, unknown> | null;
  occurred_at: string | null;
  indexed_at: string | null;
  project_id: string | null;
};

export function useActivity(source?: string) {
  return useQuery<ActivityEvent[]>({
    queryKey: ['activity', source ?? 'all'],
    queryFn: () => {
      const qs = source ? `?source=${encodeURIComponent(source)}` : '';
      return api.get<ActivityEvent[]>(`/activity${qs}`);
    },
    staleTime: 15_000,
  });
}
