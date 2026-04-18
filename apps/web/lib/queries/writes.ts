'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { TargetCandidate } from '@axis/design-system';
import { api } from '../api';

export function useConfirmWrite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (writeActionId: string) =>
      api.post<{ ok: boolean; status: string }>(
        `/writes/${writeActionId}/confirm`,
        {},
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent'] }),
  });
}

export function useRollbackWrite() {
  return useMutation({
    mutationFn: (writeActionId: string) =>
      api.post<{ ok: boolean; status: string }>(
        `/writes/${writeActionId}/rollback`,
        {},
      ),
  });
}

interface ChooseTargetVars {
  writeId: string;
  chosen: TargetCandidate;
}

export function useChooseTarget() {
  return useMutation({
    mutationFn: async ({ writeId, chosen }: ChooseTargetVars) =>
      api.post<{ ok: boolean; write_id: string; target_id: string }>(
        `/writes/${writeId}/choose-target`,
        { chosen },
      ),
  });
}
