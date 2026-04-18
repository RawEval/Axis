'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export type OAuthApp = {
  tool: string;
  client_id?: string;
  client_secret?: string;
  redirect_uri?: string | null;
  is_custom: boolean;
  created_at?: string;
  updated_at?: string;
};

export function useOAuthApps() {
  return useQuery<OAuthApp[]>({
    queryKey: ['oauth-apps'],
    queryFn: () => api.get<OAuthApp[]>('/oauth-apps'),
    staleTime: 60_000,
  });
}

export function useOAuthApp(tool: string) {
  return useQuery<OAuthApp>({
    queryKey: ['oauth-apps', tool],
    queryFn: () => api.get<OAuthApp>(`/oauth-apps/${tool}`),
    staleTime: 60_000,
  });
}

export function useSaveOAuthApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      tool,
      client_id,
      client_secret,
      redirect_uri,
    }: {
      tool: string;
      client_id: string;
      client_secret: string;
      redirect_uri?: string;
    }) =>
      api.put<OAuthApp>(`/oauth-apps/${tool}`, {
        client_id,
        client_secret,
        redirect_uri,
      }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['oauth-apps'] });
      qc.invalidateQueries({ queryKey: ['oauth-apps', vars.tool] });
    },
  });
}

export function useDeleteOAuthApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tool: string) => api.delete<{ deleted: boolean }>(`/oauth-apps/${tool}`),
    onSuccess: (_, tool) => {
      qc.invalidateQueries({ queryKey: ['oauth-apps'] });
      qc.invalidateQueries({ queryKey: ['oauth-apps', tool] });
    },
  });
}
