'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { History as HistoryIcon, Search } from 'lucide-react';
import {
  Badge,
  Button,
  Input,
  SegmentedControl,
  Skeleton,
} from '@axis/design-system';
import { rightPanel } from '@/lib/right-panel';
import { useAgentHistory, type AgentAction } from '@/lib/queries/agent';

type StatusFilter = 'all' | 'done' | 'failed';

const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'done', label: 'Done' },
  { value: 'failed', label: 'Failed' },
] as const;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function deriveStatus(action: AgentAction): 'done' | 'failed' {
  const result = action.result;
  if (result && typeof result === 'object' && 'error' in (result as object)) {
    return 'failed';
  }
  return 'done';
}

function deriveTokens(action: AgentAction): number {
  const result = action.result;
  if (result && typeof result === 'object' && 'tokens_used' in (result as object)) {
    return (result as { tokens_used?: number }).tokens_used ?? 0;
  }
  return 0;
}

export default function HistoryPage() {
  const router = useRouter();
  const { data, isLoading, error } = useAgentHistory();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.filter((a) => {
      const status = deriveStatus(a);
      if (statusFilter !== 'all' && status !== statusFilter) return false;
      if (q && !a.prompt.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, query, statusFilter]);

  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-8 px-6 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">History</h1>
        <p className="text-body text-ink-secondary">Past runs and their outputs.</p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            size={14}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-tertiary"
          />
          <Input
            placeholder="Search runs…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <SegmentedControl
          value={statusFilter}
          onChange={(v) => setStatusFilter(v as StatusFilter)}
          options={STATUS_OPTIONS}
          aria-label="Filter by status"
        />
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-body-s text-danger">
          Failed to load history.
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <EmptyHistory onStart={() => router.push('/chat')} />
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-12 border border-dashed border-edge-subtle rounded-lg">
          <p className="text-body-s text-ink-tertiary">No runs match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-edge-subtle">
          {filtered.map((a) => {
            const status = deriveStatus(a);
            const tokens = deriveTokens(a);
            return (
              <button
                key={a.id}
                type="button"
                onClick={() =>
                  rightPanel.open({
                    title: a.prompt.slice(0, 80),
                    body: <RunDetailPanel action={a} />,
                  })
                }
                className="w-full flex items-center gap-4 px-4 py-3 border-b border-edge-subtle last:border-b-0 text-left hover:bg-canvas-elevated transition-colors"
              >
                <span className="font-mono text-mono-s text-ink-tertiary tabular-nums w-32 flex-shrink-0">
                  {formatTimestamp(a.timestamp)}
                </span>
                <span className="flex-1 text-body-s text-ink truncate">{a.prompt}</span>
                {tokens > 0 && (
                  <span className="font-mono text-mono-s text-ink-tertiary tabular-nums hidden sm:inline">
                    {tokens} tok
                  </span>
                )}
                <Badge tone={status === 'done' ? 'success' : 'danger'} dot>
                  {status}
                </Badge>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EmptyHistory({ onStart }: { onStart: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 border border-dashed border-edge-subtle rounded-lg">
      <HistoryIcon size={36} className="text-ink-tertiary" aria-hidden="true" />
      <div className="text-center space-y-1">
        <p className="font-display text-heading-1 text-ink">No past runs</p>
        <p className="text-body-s text-ink-tertiary">
          Your run history appears here once Axis starts working.
        </p>
      </div>
      <Button variant="primary" size="sm" onClick={onStart}>
        Start a run
      </Button>
    </div>
  );
}

function RunDetailPanel({ action }: { action: AgentAction }) {
  const status = deriveStatus(action);
  const tokens = deriveTokens(action);
  const resultText =
    action.result && typeof action.result === 'object'
      ? JSON.stringify(action.result, null, 2)
      : String(action.result ?? '');
  const planText =
    action.plan && typeof action.plan === 'object'
      ? JSON.stringify(action.plan, null, 2)
      : String(action.plan ?? '');

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Badge tone={status === 'done' ? 'success' : 'danger'} dot>
          {status}
        </Badge>
        <span className="font-mono text-mono-s text-ink-tertiary tabular-nums">
          {formatTimestamp(action.timestamp)}
        </span>
        {tokens > 0 && (
          <span className="font-mono text-mono-s text-ink-tertiary tabular-nums">
            {tokens} tok
          </span>
        )}
      </div>

      <section>
        <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Prompt
        </h3>
        <p className="text-body-s text-ink whitespace-pre-wrap">{action.prompt}</p>
      </section>

      {planText && planText !== 'null' && (
        <section>
          <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Plan
          </h3>
          <pre className="overflow-auto rounded-md border border-edge-subtle bg-canvas-elevated p-3 font-mono text-mono-s text-ink-secondary">
            {planText}
          </pre>
        </section>
      )}

      {resultText && resultText !== 'null' && (
        <section>
          <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Result
          </h3>
          <pre className="overflow-auto rounded-md border border-edge-subtle bg-canvas-elevated p-3 font-mono text-mono-s text-ink-secondary">
            {resultText}
          </pre>
        </section>
      )}
    </div>
  );
}
