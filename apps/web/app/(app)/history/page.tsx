'use client';

import { Badge, Button, PageHeader } from '@/components/ui';
import { useAgentHistory } from '@/lib/queries/agent';

export default function HistoryPage() {
  const { data, isLoading, error } = useAgentHistory();

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-6 px-6 py-6">
      <PageHeader title="History" />

      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger-fg">
          Failed to load history
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg border border-edge bg-canvas-raised" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="rounded-lg border border-edge bg-canvas-raised px-5 py-8 text-center">
          <div className="mb-1 text-sm font-medium text-ink">No runs yet</div>
          <div className="text-xs text-ink-tertiary">Ask Axis a question to see your history here.</div>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => (window.location.href = '/chat')}>
            Go to Ask
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {data.map((a) => {
            const tokens =
              typeof a.result === 'object' && a.result !== null && 'tokens_used' in (a.result as object)
                ? ((a.result as { tokens_used?: number }).tokens_used ?? 0)
                : 0;
            return (
              <div
                key={a.id}
                className="flex items-center gap-3 rounded-lg border border-edge bg-canvas-raised px-4 py-3 transition-colors hover:bg-canvas-subtle"
              >
                <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-brand-50 text-xs font-bold text-brand-600">
                  Q
                </div>
                <div className="flex-1 min-w-0">
                  <div className="truncate text-sm text-ink">{a.prompt}</div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-3 text-xs">
                  {tokens > 0 && (
                    <span className="rounded bg-canvas-subtle px-2 py-0.5 text-ink-tertiary">{tokens} tok</span>
                  )}
                  <Badge tone="success">done</Badge>
                  <span className="text-ink-tertiary">{new Date(a.timestamp).toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
