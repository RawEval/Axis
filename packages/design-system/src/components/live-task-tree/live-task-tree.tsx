'use client';

import clsx from 'clsx';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState, type ReactNode } from 'react';

export type StepState = 'pending' | 'running' | 'done' | 'failed' | 'denied' | 'awaiting';

export interface StepToolCall {
  name: string;
  args?: unknown;
  result?: unknown;
}

export interface StepData {
  id: string;
  label: string;
  state: StepState;
  durationMs?: number;
  toolCall?: StepToolCall;
  children?: ReadonlyArray<StepData>;
}

const STATE_DOT: Record<StepState, string> = {
  pending:  'bg-agent-background',
  running:  'bg-agent-running animate-breathe',
  done:     'bg-success',
  failed:   'bg-danger',
  denied:   'bg-warning',
  awaiting: 'bg-agent-awaiting animate-breathe',
};

const STATE_LABEL: Record<StepState, string> = {
  pending:  'pending',
  running:  'running',
  done:     'done',
  failed:   'failed',
  denied:   'denied',
  awaiting: 'awaiting',
};

function formatDuration(ms?: number): string | null {
  if (ms == null) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StepRow({ step, depth }: { step: StepData; depth: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasTool = step.toolCall != null;
  const duration = formatDuration(step.durationMs);

  return (
    <div className="flex flex-col">
      <div
        className="flex items-center gap-3 px-2 py-1 font-mono text-mono-s text-ink-secondary"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        <span aria-hidden="true" className={clsx('inline-block h-2 w-2 rounded-full shrink-0', STATE_DOT[step.state])} />
        <span className={clsx('flex-1 truncate', step.state === 'running' && 'text-ink')}>
          {step.label}
        </span>
        <span className="sr-only">{STATE_LABEL[step.state]}</span>
        {duration && (
          <span className="text-ink-tertiary tabular-nums">{duration}</span>
        )}
        {hasTool && (
          <button
            type="button"
            aria-label={`Expand ${step.toolCall?.name}`}
            onClick={() => setExpanded((v) => !v)}
            className="text-ink-tertiary hover:text-ink-secondary"
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
      </div>

      {hasTool && expanded && (
        <div
          className="mb-1 rounded-sm border border-edge-subtle bg-canvas-elevated px-3 py-2 font-mono text-mono-s text-ink-secondary"
          style={{ marginLeft: `${depth * 16 + 24}px` }}
        >
          <div className="text-ink-tertiary">tool_call: {step.toolCall?.name}</div>
          {step.toolCall?.args !== undefined && (
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap">
              args: {JSON.stringify(step.toolCall.args, null, 2)}
            </pre>
          )}
          {step.toolCall?.result !== undefined && (
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap">
              → {JSON.stringify(step.toolCall.result, null, 2)}
            </pre>
          )}
        </div>
      )}

      {step.children && step.children.length > 0 && (
        <div className="flex flex-col">
          {step.children.map((child) => (
            <StepRow key={child.id} step={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export interface LiveTaskTreeProps {
  steps: ReadonlyArray<StepData>;
  /** Optional content rendered at the bottom (e.g. "Thinking…" pulse). */
  trailing?: ReactNode;
}

export function LiveTaskTree({ steps, trailing }: LiveTaskTreeProps) {
  if (steps.length === 0 && !trailing) return null;
  return (
    <div className="flex flex-col gap-0">
      {steps.map((s) => (
        <StepRow key={s.id} step={s} depth={0} />
      ))}
      {trailing}
    </div>
  );
}
