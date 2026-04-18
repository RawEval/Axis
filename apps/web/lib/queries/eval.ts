'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type CorrectionType = 'wrong' | 'rewrite' | 'memory_update' | 'scope';

export type EvalScoreRow = {
  id: string;
  action_id: string;
  rubric_type: string;
  scores: Array<{ dimension: string; score: number; reason: string }>;
  composite_score: number | null;
  flagged: boolean;
  created_at: string;
  prompt: string;
};

export function useSubmitCorrection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      action_id: string;
      correction_type: CorrectionType;
      note?: string;
    }) => api.post<{ id: string; created_at: string }>('/eval/corrections', input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['eval', 'scores'] });
    },
  });
}

export function useEvalScores(limit = 50) {
  return useQuery<EvalScoreRow[]>({
    queryKey: ['eval', 'scores', limit],
    queryFn: () => api.get<EvalScoreRow[]>(`/eval/scores?limit=${limit}`),
    staleTime: 30_000,
  });
}
