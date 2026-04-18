'use client';

import {
  LiveTaskTree as LiveTaskTreeUI,
  type StepData,
  type StepState,
} from '@axis/design-system';
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
 *
 * The accumulated cards are then translated into the design-system
 * primitive's `StepData` shape and rendered via `LiveTaskTreeUI`.
 */
export function LiveTaskTree({ events }: { events: LiveEvent[] }) {
  const cards = accumulateSteps(events);
  const last = events[events.length - 1];
  const completed = events.some(
    (e) => e.type === 'task.completed' || e.type === 'task.failed',
  );
  const running = Boolean(last) && !completed;

  const steps: StepData[] = cards.map((c, i) => ({
    id: `${c.step}:${c.name}:${i}`,
    label: c.summary ? `${c.name || c.kind} — ${c.summary}` : c.name || c.kind,
    state: STATUS_TO_STATE[c.status],
  }));

  const trailing =
    running && cards.every((s) => s.status !== 'running') ? (
      <div className="flex items-center gap-2 px-2 py-1 font-mono text-mono-s text-ink-tertiary">
        <span aria-hidden className="inline-block h-2 w-2 animate-breathe rounded-full bg-agent-running" />
        Thinking…
      </div>
    ) : null;

  if (steps.length === 0 && !trailing) return null;

  return <LiveTaskTreeUI steps={steps} trailing={trailing} />;
}

type StepCardStatus =
  | 'running'
  | 'done'
  | 'error'
  | 'denied'
  | 'awaiting_permission';

type StepCard = {
  step: number;
  kind: string;
  name: string;
  status: StepCardStatus;
  summary: string | null;
};

const STATUS_TO_STATE: Record<StepCardStatus, StepState> = {
  running: 'running',
  done: 'done',
  error: 'failed',
  denied: 'denied',
  awaiting_permission: 'awaiting',
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
      const status = (String(payload.status ?? 'done') as StepCardStatus) ?? 'done';
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
