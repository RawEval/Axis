'use client';

import type { LiveEvent } from '@/lib/queries/live';

/**
 * Renders the live task plan as it streams from the WebSocket.
 *
 * Event protocol (from services/agent-orchestration/app/events.py):
 *   task.started        — supervisor began a /run
 *   step.started        — a tool_use block is about to dispatch
 *   step.completed      — the capability returned (status: done|error|denied)
 *   permission.request  — gated capability waiting for user approval
 *   task.completed      — final synthesise step finished
 *   task.failed         — supervisor aborted
 *
 * We collapse the stream into a per-step "card" keyed on
 * ``payload.step + payload.name``. Later events for the same step mutate
 * the card's status/summary so the UI looks like a tree that fills in.
 */
export function LiveTaskTree({ events }: { events: LiveEvent[] }) {
  const steps = accumulateSteps(events);
  const last = events[events.length - 1];
  const completed = events.some(
    (e) => e.type === 'task.completed' || e.type === 'task.failed',
  );
  const running = last && !completed;

  if (steps.length === 0 && !running) {
    return null;
  }

  return (
    <div className="flex flex-col gap-1 font-mono text-xs">
      {steps.map((s, i) => (
        <StepRow key={i} step={s} />
      ))}
      {running && steps.every((s) => s.status !== 'running') && (
        <div className="flex items-center gap-2 text-ink-tertiary">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-brand-500" />
          Thinking…
        </div>
      )}
    </div>
  );
}

type StepStatus = 'running' | 'done' | 'error' | 'denied' | 'awaiting_permission';

type StepCard = {
  step: number;
  kind: string;
  name: string;
  status: StepStatus;
  summary: string | null;
};

function accumulateSteps(events: LiveEvent[]): StepCard[] {
  const byKey = new Map<string, StepCard>();

  for (const ev of events) {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const step = Number(payload.step ?? 0);
    const name = String(payload.name ?? payload.capability ?? '');
    const kind = String(payload.kind ?? 'tool_use');
    const key = `${step}:${name}`;

    if (ev.type === 'permission.request') {
      const capability = String(payload.capability ?? '');
      byKey.set(`permission:${capability}`, {
        step: step || byKey.size + 1,
        kind: 'permission',
        name: capability,
        status: 'awaiting_permission',
        summary: String(payload.description ?? 'Awaiting your approval'),
      });
      continue;
    }

    if (ev.type === 'step.started') {
      byKey.delete(`permission:${name}`);
      byKey.set(key, {
        step,
        kind,
        name,
        status: 'running',
        summary: null,
      });
      continue;
    }

    if (ev.type === 'step.completed') {
      const status = (String(payload.status ?? 'done') as StepStatus) ?? 'done';
      const existing = byKey.get(key);
      byKey.set(key, {
        step,
        kind: existing?.kind ?? kind,
        name,
        status,
        summary: payload.summary != null ? String(payload.summary) : existing?.summary ?? null,
      });
    }
  }

  return [...byKey.values()].sort((a, b) => a.step - b.step);
}

function StepRow({ step }: { step: StepCard }) {
  const { status } = step;
  const dot = {
    running: 'bg-brand-500 animate-pulse',
    done: 'bg-success',
    error: 'bg-danger',
    denied: 'bg-warning',
    awaiting_permission: 'bg-warning animate-pulse',
  }[status];
  const label = {
    running: 'running',
    done: 'done',
    error: 'error',
    denied: 'denied',
    awaiting_permission: 'awaiting permission',
  }[status];
  return (
    <div className="flex items-start gap-2">
      <span className={`mt-1 inline-block h-2 w-2 shrink-0 rounded-full ${dot}`} />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-ink">{step.name || step.kind}</span>
          <span className="text-ink-tertiary">· {label}</span>
        </div>
        {step.summary && (
          <div className="mt-0.5 text-ink-tertiary">{step.summary}</div>
        )}
      </div>
    </div>
  );
}
