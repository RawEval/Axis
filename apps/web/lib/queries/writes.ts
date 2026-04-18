'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
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
