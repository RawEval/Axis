'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  PromptInput,
  WritePreviewCard,
  type TargetCandidate,
} from '@axis/design-system';
import { Button } from '@/components/ui';
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
import {
  useChooseTarget,
  useConfirmWrite,
  useRollbackWrite,
} from '@/lib/queries/writes';

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

const SUGGESTED_PROMPTS: ReadonlyArray<string> = [
  'Summarize what happened in #product on Slack today',
  'Draft a Q3 retro in Notion',
  'Triage my Gmail inbox',
];

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageContent() {
  const params = useSearchParams();
  const initialPrompt = params.get('prompt') ?? '';

  const [prompt, setPrompt] = useState(initialPrompt);
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
  const chooseTarget = useChooseTarget();
  const { events, clear: clearEvents } = useLiveEvents();
  const [chooseBusyId, setChooseBusyId] = useState<string | null>(null);

  const pendingTargetPick = useMemo<{
    writeId: string;
    tool: string;
    options: TargetCandidate[];
  } | null>(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      if (ev.type !== 'write.target_pick_required') continue;
      const payload = (ev.payload ?? {}) as Record<string, unknown>;
      const writeId = String(payload.write_action_id ?? '');
      if (!writeId) continue;
      const resolved = events.slice(i + 1).some((later) => {
        const p = (later.payload ?? {}) as Record<string, unknown>;
        const otherId = String(p.write_action_id ?? '');
        return (
          otherId === writeId &&
          (later.type === 'write.target_chosen' ||
            later.type === 'write.preview' ||
            later.type === 'write.confirmed' ||
            later.type === 'write.rolled_back')
        );
      });
      if (resolved) continue;
      const options = ((payload.options ?? []) as TargetCandidate[]) ?? [];
      return {
        writeId,
        tool: String(payload.tool ?? ''),
        options,
      };
    }
    return null;
  }, [events]);

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
    return undefined;
  }, [events, clearEvents]);

  const runPrompt = async (text: string) => {
    setError(null);
    if (!text.trim()) return;
    try {
      const result = (await run.mutateAsync(text)) as RunResult;
      setLastResult(result);
      setPrompt('');
      setCorrectionOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? (typeof err.detail === 'string' ? err.detail : 'Agent run failed') : 'Agent run failed');
    }
  };

  const onSubmit = (text: string) => {
    void runPrompt(text);
  };

  const citationCount = lastResult?.citations?.length ?? 0;
  const isEmpty = !lastResult && !run.isPending && events.length === 0;

  return (
    <div className="flex h-full flex-col">
      {/* Permission modal overlay */}
      {pendingPermission && (
        <PermissionModal
          request={pendingPermission}
          onResolved={() => setDismissedPendings((prev) => [...prev, pendingPermission.pending_id])}
        />
      )}

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-6 py-10">
          {isEmpty ? (
            <EmptyState onPick={(p) => setPrompt(p)} />
          ) : (
            <>
              {/* Live progress — only visible during a run */}
              {(run.isPending || events.length > 0) && (
                <div className="rounded-lg border border-edge bg-canvas-surface px-4 py-3">
                  <div className="mb-2 flex items-center gap-2 text-xs text-ink-tertiary">
                    <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                    Working...
                  </div>
                  <LiveTaskTree events={events} />
                </div>
              )}

              {/* Write target pick — disambiguation before send */}
              {pendingTargetPick && (
                <WritePreviewCard
                  title={`${pendingTargetPick.tool} · Pick recipient`}
                  onConfirm={() => {}}
                  onCancel={() => {}}
                  targetOptions={pendingTargetPick.options}
                  chooseBusy={chooseBusyId}
                  onChooseTarget={async (chosen) => {
                    setChooseBusyId(chosen.id);
                    try {
                      await chooseTarget.mutateAsync({
                        writeId: pendingTargetPick.writeId,
                        chosen,
                      });
                    } catch {
                      /* surface via error state in future */
                    } finally {
                      setChooseBusyId(null);
                    }
                  }}
                />
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
                  <div className="rounded-lg border border-warning/30 bg-warning/30 p-4">
                    <div className="mb-2 text-xs font-semibold text-warning">Write preview - {tool}</div>
                    <DiffViewer lines={diffLines.map((l) => ({ type: l.type as 'add' | 'del' | 'eq', text: l.text }))} />
                    <div className="mt-3 flex gap-2">
                      <Button variant="primary" size="sm" disabled={confirmWrite.isPending || confirmed} onClick={() => confirmWrite.mutate(writeId)}>
                        {confirmWrite.isPending ? 'Confirming...' : confirmed ? 'Done' : 'Confirm'}
                      </Button>
                      <Button variant="ghost" size="sm" disabled={rollbackWrite.isPending || confirmed} onClick={() => rollbackWrite.mutate(writeId)}>
                        Reject
                      </Button>
                    </div>
                  </div>
                );
              })()}

              {/* Last result */}
              {lastResult && (
                <div className="flex flex-col gap-3">
                  <div className="rounded-lg border border-edge bg-canvas-surface p-5">
                    {lastResult.output ? (
                      <CitedResponse content={lastResult.output} citations={lastResult.citations ?? []} />
                    ) : (
                      <div className="text-sm text-ink-tertiary">(empty response)</div>
                    )}
                  </div>

                  {/* Meta row */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {typeof lastResult.latency_ms === 'number' && (
                      <span className="rounded bg-canvas-elevated px-2 py-0.5 text-ink-tertiary">{lastResult.latency_ms}ms</span>
                    )}
                    {typeof lastResult.tokens_used === 'number' && (
                      <span className="rounded bg-canvas-elevated px-2 py-0.5 text-ink-tertiary">{lastResult.tokens_used} tokens</span>
                    )}
                    {citationCount > 0 && (
                      <span className="rounded bg-accent-subtle px-2 py-0.5 text-accent">{citationCount} source{citationCount === 1 ? '' : 's'}</span>
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
                    <div className="rounded-lg border border-edge bg-canvas-elevated p-4">
                      <div className="mb-3 flex flex-wrap gap-1.5">
                        {(['wrong', 'rewrite', 'memory_update', 'scope'] as CorrectionType[]).map((t) => (
                          <button
                            key={t}
                            className={`rounded-md px-2.5 py-1 text-xs transition-colors ${correctionType === t ? 'bg-accent text-white' : 'bg-canvas-surface text-ink-secondary hover:bg-canvas-sunken'}`}
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
                        className="mb-3 w-full rounded-md border border-edge-strong bg-canvas-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent"
                      />
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
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
            </>
          )}
        </div>
      </div>

      {/* Sticky bottom prompt */}
      <div className="border-t border-edge-subtle bg-canvas-surface">
        <div className="mx-auto w-full max-w-[860px] px-6 py-4">
          <PromptInput
            value={prompt}
            onChange={setPrompt}
            onSubmit={onSubmit}
            busy={run.isPending}
            placeholder="Type a message, or /command"
            aria-label="Prompt"
          />
          {error && (
            <div className="mt-2 rounded-md border border-danger/20 bg-danger/10 px-3 py-2 text-xs text-danger">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-20 text-center">
      <h1 className="font-display text-display-l text-ink">What should Axis do?</h1>
      <p className="text-body text-ink-secondary max-w-prose">
        Pick a starter or write your own. Axis can read and write across your connected tools.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-[640px] w-full">
        {SUGGESTED_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick(p)}
            className="block p-4 rounded-md border border-edge-subtle bg-canvas-surface text-left hover:border-edge hover:bg-canvas-elevated transition-colors"
          >
            <span className="text-body-s text-ink">{p}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
