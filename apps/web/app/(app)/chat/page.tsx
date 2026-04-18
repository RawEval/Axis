'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Panel,
  PanelBody,
  PanelFooter,
  PanelHeader,
} from '@/components/ui';
import { CitedResponse, type Citation } from '@/components/chat/cited-response';
import { LiveTaskTree } from '@/components/chat/live-task-tree';
import {
  PermissionModal,
  type PermissionRequest,
} from '@/components/chat/permission-modal';
import { DiffViewer } from '@/components/diff-viewer';
import { ApiError } from '@/lib/api';
import { useRunAgent } from '@/lib/queries/agent';
import { useSubmitCorrection, type CorrectionType } from '@/lib/queries/eval';
import { useLiveEvents } from '@/lib/queries/live';
import { useConfirmWrite, useRollbackWrite } from '@/lib/queries/writes';

type RunResult = {
  action_id?: string;
  message_id?: string;
  output?: string;
  project_id?: string | null;
  project_scope?: string;
  plan?: Array<Record<string, unknown>>;
  citations?: Citation[];
  tokens_used?: number;
  latency_ms?: number;
};

export default function ChatPage() {
  const [prompt, setPrompt] = useState('');
  const [lastResult, setLastResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [correctionOpen, setCorrectionOpen] = useState(false);
  const [correctionType, setCorrectionType] = useState<CorrectionType>('wrong');
  const [correctionNote, setCorrectionNote] = useState('');
  const [correctionStatus, setCorrectionStatus] = useState<string | null>(null);
  const [dismissedPendings, setDismissedPendings] = useState<string[]>([]);

  const run = useRunAgent();
  const submitCorrection = useSubmitCorrection();
  const confirmWrite = useConfirmWrite();
  const rollbackWrite = useRollbackWrite();
  const { events, clear: clearEvents, connected } = useLiveEvents();

  const pendingPermission = useMemo<PermissionRequest | null>(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      if (ev.type !== 'permission.request') continue;
      const payload = (ev.payload ?? {}) as Record<string, unknown>;
      const pendingId = String(payload.pending_id ?? '');
      if (!pendingId || dismissedPendings.includes(pendingId)) continue;
      const capability = String(payload.capability ?? '');
      const resolved = events.slice(i + 1).some((later) => {
        const p = (later.payload ?? {}) as Record<string, unknown>;
        return (later.type === 'step.started' || later.type === 'step.completed') && String(p.name ?? '') === capability;
      });
      if (resolved) continue;
      return {
        pending_id: pendingId,
        capability,
        description: String(payload.description ?? ''),
        inputs: (payload.inputs ?? {}) as Record<string, unknown>,
      };
    }
    return null;
  }, [events, dismissedPendings]);

  useEffect(() => {
    if (events.some((e) => e.type === 'task.completed' || e.type === 'task.failed')) {
      const timer = setTimeout(() => clearEvents(), 1500);
      return () => clearTimeout(timer);
    }
  }, [events, clearEvents]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!prompt.trim()) return;
    try {
      const result = (await run.mutateAsync(prompt)) as RunResult;
      setLastResult(result);
      setPrompt('');
      setCorrectionOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? (typeof err.detail === 'string' ? err.detail : 'Agent run failed') : 'Agent run failed');
    }
  };

  const citationCount = lastResult?.citations?.length ?? 0;

  return (
    <div className="flex min-h-full flex-col">
      {/* Permission modal overlay */}
      {pendingPermission && (
        <PermissionModal
          request={pendingPermission}
          onResolved={() => setDismissedPendings((prev) => [...prev, pendingPermission.pending_id])}
        />
      )}

      {/* Main content — conversation style */}
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-6 py-6">
        {/* Live progress — only visible during a run */}
        {(run.isPending || events.length > 0) && (
          <div className="rounded-lg border border-edge bg-canvas-raised px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-xs text-ink-tertiary">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" />
              Working...
            </div>
            <LiveTaskTree events={events} />
          </div>
        )}

        {/* Write preview */}
        {events.some((e) => e.type === 'write.preview') && (() => {
          const previewEv = [...events].reverse().find((e) => e.type === 'write.preview');
          const payload = (previewEv?.payload ?? {}) as Record<string, unknown>;
          const writeId = String(payload.write_action_id ?? '');
          const diffLines = (payload.diff_lines ?? []) as Array<{ type: string; text: string }>;
          const tool = String(payload.tool ?? '');
          const confirmed = events.some((e) => e.type === 'write.confirmed');
          return (
            <div className="rounded-lg border border-warning/30 bg-warning-bg/30 p-4">
              <div className="mb-2 text-xs font-semibold text-warning-fg">Write preview - {tool}</div>
              <DiffViewer lines={diffLines.map((l) => ({ type: l.type as 'add' | 'del' | 'eq', text: l.text }))} />
              <div className="mt-3 flex gap-2">
                <Button variant="primary" size="xs" disabled={confirmWrite.isPending || confirmed} onClick={() => confirmWrite.mutate(writeId)}>
                  {confirmWrite.isPending ? 'Confirming...' : confirmed ? 'Done' : 'Confirm'}
                </Button>
                <Button variant="ghost" size="xs" disabled={rollbackWrite.isPending || confirmed} onClick={() => rollbackWrite.mutate(writeId)}>
                  Reject
                </Button>
              </div>
            </div>
          );
        })()}

        {/* Last result */}
        {lastResult && (
          <div className="flex flex-col gap-3">
            <div className="rounded-lg border border-edge bg-canvas-raised p-5">
              {lastResult.output ? (
                <CitedResponse content={lastResult.output} citations={lastResult.citations ?? []} />
              ) : (
                <div className="text-sm text-ink-tertiary">(empty response)</div>
              )}
            </div>

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {typeof lastResult.latency_ms === 'number' && (
                <span className="rounded bg-canvas-subtle px-2 py-0.5 text-ink-tertiary">{lastResult.latency_ms}ms</span>
              )}
              {typeof lastResult.tokens_used === 'number' && (
                <span className="rounded bg-canvas-subtle px-2 py-0.5 text-ink-tertiary">{lastResult.tokens_used} tokens</span>
              )}
              {citationCount > 0 && (
                <span className="rounded bg-brand-50 px-2 py-0.5 text-brand-600">{citationCount} source{citationCount === 1 ? '' : 's'}</span>
              )}
              <button
                className="ml-auto text-ink-tertiary transition-colors hover:text-ink"
                onClick={() => { setCorrectionOpen((v) => !v); setCorrectionStatus(null); }}
              >
                {correctionOpen ? 'Cancel' : 'Flag issue'}
              </button>
            </div>

            {/* Correction form */}
            {correctionOpen && lastResult.action_id && (
              <div className="rounded-lg border border-edge bg-canvas-subtle p-4">
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {(['wrong', 'rewrite', 'memory_update', 'scope'] as CorrectionType[]).map((t) => (
                    <button
                      key={t}
                      className={`rounded-md px-2.5 py-1 text-xs transition-colors ${correctionType === t ? 'bg-brand-500 text-white' : 'bg-canvas-raised text-ink-secondary hover:bg-canvas-sunken'}`}
                      onClick={() => setCorrectionType(t)}
                    >
                      {t.replace('_', ' ')}
                    </button>
                  ))}
                </div>
                <textarea
                  value={correctionNote}
                  onChange={(e) => setCorrectionNote(e.target.value)}
                  rows={2}
                  placeholder="What should be different next time?"
                  className="mb-3 w-full rounded-md border border-edge-strong bg-canvas-raised px-3 py-2 text-sm text-ink outline-none focus:border-brand-500"
                />
                <div className="flex items-center gap-2">
                  <Button
                    size="xs"
                    variant="primary"
                    disabled={submitCorrection.isPending}
                    onClick={async () => {
                      setCorrectionStatus(null);
                      try {
                        await submitCorrection.mutateAsync({
                          action_id: lastResult.action_id!,
                          correction_type: correctionType,
                          note: correctionNote.trim() || undefined,
                        });
                        setCorrectionStatus('Recorded');
                        setCorrectionNote('');
                        setCorrectionOpen(false);
                      } catch { setCorrectionStatus('Failed'); }
                    }}
                  >
                    {submitCorrection.isPending ? 'Sending...' : 'Submit'}
                  </Button>
                  {correctionStatus && <span className="text-xs text-ink-tertiary">{correctionStatus}</span>}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!lastResult && !run.isPending && (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <div className="mb-2 text-2xl font-semibold tracking-tight text-ink">What can I help with?</div>
              <div className="text-sm text-ink-tertiary">Ask anything about your connected workspace.</div>
            </div>
          </div>
        )}
      </div>

      {/* Command bar — pinned to bottom */}
      <div className="sticky bottom-0 border-t border-edge bg-canvas-raised px-6 py-4">
        <form onSubmit={onSubmit} className="mx-auto max-w-3xl">
          <div className="flex items-end gap-3 rounded-xl border border-edge-strong bg-canvas p-3 shadow-panel focus-within:border-brand-500 focus-within:shadow-popover transition-shadow">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={1}
              placeholder="Ask Axis anything..."
              className="flex-1 resize-none bg-transparent text-sm text-ink outline-none placeholder:text-ink-disabled"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit(e); }
              }}
              onInput={(e) => {
                const t = e.currentTarget;
                t.style.height = 'auto';
                t.style.height = `${Math.min(t.scrollHeight, 160)}px`;
              }}
            />
            <div className="flex items-center gap-2">
              <span className={`inline-block h-1.5 w-1.5 rounded-full ${connected ? 'bg-success' : 'bg-ink-disabled'}`} title={connected ? 'Live' : 'Offline'} />
              <Button variant="primary" size="sm" type="submit" disabled={run.isPending || !prompt.trim()}>
                {run.isPending ? 'Running...' : 'Send'}
              </Button>
            </div>
          </div>
          {error && (
            <div className="mt-2 rounded-md border border-danger/20 bg-danger-bg px-3 py-2 text-xs text-danger-fg">
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
