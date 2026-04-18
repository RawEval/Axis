'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

/**
 * Mirrors the response of `GET /admin/stats` in
 * `services/api-gateway/app/routes/admin.py::system_stats`.
 *
 * `avg_eval_composite` is a 0–10 score (ROUND(AVG(composite_score), 2)),
 * not a 0–1 fraction — render as a raw number, do not multiply by 100.
 */
export interface AdminStats {
  users: number;
  organizations: number;
  projects: number;
  total_runs: number;
  connected_tools: number;
  eval_scores: number;
  corrections: number;
  indexed_resources: number;
  avg_latency_ms: number | null;
  avg_eval_composite: number | null;
}

/** Mirrors `GET /admin/connectors` rows. */
export interface AdminConnector {
  id: string;
  tool: string;
  status: string;
  health: string | null;
  workspace: string | null;
  last_sync: string | null;
  user_email: string;
  project: string | null;
}

/** Mirrors `GET /admin/runs` rows. */
export interface AdminRun {
  id: string;
  prompt: string | null;
  timestamp: string;
  user: string;
  tokens: number | null;
  latency_ms: number | null;
  composite_score: number | null;
  flagged: boolean | null;
}

/**
 * Mirrors `GET /admin/eval` rows — backed by the `admin_eval_trend` view.
 * The route returns up to 90 rows (one per date × rubric); the page derives
 * a summary from the response.
 */
export interface AdminEvalRow {
  date: string;
  rubric: string;
  count: number;
  avg_composite: number | null;
  flagged: number;
  flagged_pct: number | null;
}

export function useAdminStats() {
  return useQuery<AdminStats>({
    queryKey: ['admin', 'stats'],
    queryFn: () => api.get<AdminStats>('/admin/stats'),
  });
}

export function useAdminConnectors() {
  return useQuery<AdminConnector[]>({
    queryKey: ['admin', 'connectors'],
    queryFn: () => api.get<AdminConnector[]>('/admin/connectors'),
  });
}

export function useAdminRuns() {
  return useQuery<AdminRun[]>({
    queryKey: ['admin', 'runs'],
    queryFn: () => api.get<AdminRun[]>('/admin/runs?limit=10'),
  });
}

export function useAdminEval() {
  return useQuery<AdminEvalRow[]>({
    queryKey: ['admin', 'eval'],
    queryFn: () => api.get<AdminEvalRow[]>('/admin/eval'),
  });
}
