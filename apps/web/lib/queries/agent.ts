'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../api';

export type AgentAction = {
  id: string;
  prompt: string;
  plan: unknown;
  result: unknown;
  eval_score: unknown;
  timestamp: string;
};

export type RunMode = 'sync' | 'background';

export type RunOptions = {
  prompt: string;
  mode?: RunMode;
  time_limit_sec?: number | null;
  notify_on_complete?: boolean;
};

export type TaskStatus = {
  task_id: string;
  prompt: string;
  status: 'planning' | 'running' | 'done' | 'failed';
  output: string;
  message_id: string | null;
  tokens_used: number;
  latency_ms: number;
  created_at: string;
  completed_at: string | null;
};

export function useAgentHistory() {
  return useQuery<AgentAction[]>({
    queryKey: ['agent', 'history'],
    queryFn: () => api.get<AgentAction[]>('/agent/history'),
    staleTime: 15_000,
  });
}

export function useRunAgent() {
  return useMutation({
    mutationFn: (opts: string | RunOptions) => {
      const body =
        typeof opts === 'string'
          ? { prompt: opts }
          : {
              prompt: opts.prompt,
              mode: opts.mode ?? 'sync',
              time_limit_sec: opts.time_limit_sec ?? undefined,
              notify_on_complete: opts.notify_on_complete ?? true,
            };
      return api.post<unknown>('/agent/run', body);
    },
  });
}

export function useTaskStatus(taskId: string | null) {
  return useQuery<TaskStatus>({
    queryKey: ['agent', 'task', taskId],
    queryFn: () => api.get<TaskStatus>(`/agent/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll every 3s while running, stop when done/failed
      if (status === 'done' || status === 'failed') return false;
      return 3000;
    },
  });
}

export function useRecentTasks(limit = 10) {
  return useQuery<TaskStatus[]>({
    queryKey: ['agent', 'tasks', limit],
    queryFn: () => api.get<TaskStatus[]>(`/agent/tasks?limit=${limit}`),
    staleTime: 10_000,
  });
}
