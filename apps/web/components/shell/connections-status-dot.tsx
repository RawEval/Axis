'use client';

import { useSyncState } from '@/lib/queries/connectors';

export function ConnectionsStatusDot() {
  const { data } = useSyncState();
  const items = data?.items ?? [];
  const anyAuthFailed = items.some((i) => i.last_status === 'auth_failed');
  const anyNotOk = items.some(
    (i) => i.last_status !== 'ok' && i.last_status !== 'never',
  );
  const cls = anyAuthFailed
    ? 'bg-red-500'
    : anyNotOk
      ? 'bg-amber-500'
      : 'bg-emerald-500';
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${cls}`}
      aria-label={
        anyAuthFailed
          ? 'connection broken'
          : anyNotOk
            ? 'connection issues'
            : 'all connections ok'
      }
      data-testid="connections-status-dot"
    />
  );
}
