'use client';

import clsx from 'clsx';
import { dismissToast, pushToast, useToasts, type ToastTone } from './toast-store';

export { useToasts, dismissToast, pushToast };

const TONE_CLASSES: Record<ToastTone, string> = {
  info:    'bg-info/10 border-info/30 text-info',
  success: 'bg-success/10 border-success/30 text-success',
  warning: 'bg-warning/10 border-warning/30 text-warning',
  danger:  'bg-danger/10 border-danger/30 text-danger',
  action:  'bg-accent-subtle border-accent/30 text-accent',
};

export function ToastViewport() {
  const { toasts } = useToasts();
  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-6 right-6 z-[60] flex flex-col gap-2 max-w-[360px] w-full pointer-events-none"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={clsx(
            'pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-md border shadow-e2 bg-canvas-surface',
            TONE_CLASSES[t.tone],
          )}
        >
          <div className="flex-1 text-body-s text-ink">{t.message}</div>
          {t.actionLabel && t.onAction && (
            <button
              type="button"
              className="font-mono text-[11px] uppercase tracking-[0.06em] text-accent hover:text-accent-hover"
              onClick={() => {
                t.onAction?.();
                dismissToast(t.id);
              }}
            >
              {t.actionLabel}
            </button>
          )}
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => dismissToast(t.id)}
            className="text-ink-tertiary hover:text-ink-secondary"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export const toast = {
  info: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'info', message, durationMs: opts.durationMs ?? 4000 }),
  success: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'success', message, durationMs: opts.durationMs ?? 4000 }),
  warning: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'warning', message, durationMs: opts.durationMs ?? 4000 }),
  error: (message: string, opts: { durationMs?: number } = {}) =>
    pushToast({ tone: 'danger', message, durationMs: opts.durationMs ?? 4000 }),
  action: (
    message: string,
    opts: { actionLabel: string; onAction: () => void; durationMs?: number },
  ) =>
    pushToast({
      tone: 'action',
      message,
      actionLabel: opts.actionLabel,
      onAction: opts.onAction,
      durationMs: opts.durationMs ?? 30_000,
    }),
};

// Re-export children for convenience
export type { ToastTone, ToastItem } from './toast-store';
