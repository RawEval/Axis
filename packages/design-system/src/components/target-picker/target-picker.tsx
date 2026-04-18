'use client';

import clsx from 'clsx';

export interface TargetCandidate {
  kind: string;
  id: string;
  label: string;
  sub_label: string | null;
  context: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface TargetPickerProps {
  candidates: ReadonlyArray<TargetCandidate>;
  onChoose: (candidate: TargetCandidate) => void;
  /** When set, the candidate with this id renders in a busy state. */
  busy?: string | null;
  /** Helper text. Default: "Pick one to continue." */
  prompt?: string;
  className?: string;
}

const ROW_BASE =
  'flex flex-col items-start gap-1 w-full text-left p-3 rounded-md border border-edge-subtle bg-canvas-surface hover:border-edge hover:bg-canvas-elevated transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

export function TargetPicker({
  candidates,
  onChoose,
  busy,
  prompt,
  className,
}: TargetPickerProps) {
  const helper = prompt ?? 'Pick one to continue.';
  return (
    <div role="group" className={clsx('space-y-3', className)}>
      <p className="text-body-s text-ink-secondary">{helper}</p>
      <div className="space-y-2">
        {candidates.map((c) => {
          const isBusy = busy === c.id;
          return (
            <button
              key={c.id}
              type="button"
              disabled={busy != null}
              aria-busy={isBusy}
              onClick={() => onChoose(c)}
              className={ROW_BASE}
            >
              <span className="text-body-s font-medium text-ink">{c.label}</span>
              {c.sub_label && (
                <span className="font-mono text-mono-s text-ink-tertiary">{c.sub_label}</span>
              )}
              {c.context && (
                <span className="text-caption text-ink-secondary line-clamp-2">{c.context}</span>
              )}
              {isBusy && (
                <span className="text-caption text-ink-tertiary mt-1">Choosing…</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
