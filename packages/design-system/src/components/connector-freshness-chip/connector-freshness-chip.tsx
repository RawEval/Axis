'use client';
import * as React from 'react';

export type ConnectorFreshnessChipProps = {
  source: string;
  state: {
    source: string;
    last_synced_at: string | null;
    last_status: 'never' | 'ok' | 'auth_failed' | 'vendor_error' | 'network_error';
    last_error: string | null;
  };
  onReconnect?: () => void;
  /** Optional test id for E2E selection. */
  'data-testid'?: string;
};

function formatRelative(iso: string | null): string {
  if (!iso) return 'never synced';
  const ageSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (ageSec < 5) return 'synced just now';
  if (ageSec < 60) return `synced ${ageSec}s ago`;
  if (ageSec < 3600) return `synced ${Math.floor(ageSec / 60)}m ago`;
  if (ageSec < 86400) return `synced ${Math.floor(ageSec / 3600)}h ago`;
  return `synced ${Math.floor(ageSec / 86400)}d ago`;
}

export function ConnectorFreshnessChip({
  source,
  state,
  onReconnect,
  'data-testid': testId,
}: ConnectorFreshnessChipProps) {
  if (state.last_status === 'auth_failed') {
    return (
      <button
        type="button"
        onClick={onReconnect}
        data-testid={testId}
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
      >
        Reconnect {source}
      </button>
    );
  }

  const ageSec = state.last_synced_at
    ? (Date.now() - new Date(state.last_synced_at).getTime()) / 1000
    : Infinity;
  const stale = ageSec > 120 || state.last_status !== 'ok';
  const colorClass = stale
    ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';

  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full ${colorClass}`}
      title={state.last_error ?? undefined}
    >
      {formatRelative(state.last_synced_at)}
    </span>
  );
}
