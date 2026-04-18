import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type StatusKind =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background' | 'done';

export interface StatusBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  status: StatusKind;
  /** Optional override label (defaults to uppercased status string). */
  label?: string;
  /** Show a breathing pulse on the dot. */
  pulse?: boolean;
}

const TONE: Record<StatusKind, string> = {
  thinking:   'text-agent-thinking bg-agent-thinking/10 border-agent-thinking/20',
  running:    'text-agent-running bg-agent-running/10 border-agent-running/20',
  awaiting:   'text-agent-awaiting bg-agent-awaiting/10 border-agent-awaiting/20',
  recovered:  'text-agent-recovered bg-agent-recovered/10 border-agent-recovered/20',
  blocked:    'text-agent-blocked bg-agent-blocked/10 border-agent-blocked/20',
  background: 'text-agent-background bg-agent-background/10 border-agent-background/20',
  done:       'text-success bg-success/10 border-success/20',
};

const DOT_BG: Record<StatusKind, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
  done:       'bg-success',
};

const BASE =
  'inline-flex items-center gap-1.5 h-5 px-2 rounded-full border font-mono text-[11px] uppercase tracking-[0.08em] tabular-nums whitespace-nowrap';

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(function StatusBadge(
  { status, label, pulse = false, className, ...rest },
  ref,
) {
  return (
    <span ref={ref} className={clsx(BASE, TONE[status], className)} {...rest}>
      <span
        aria-hidden="true"
        className={clsx('h-1.5 w-1.5 rounded-full', DOT_BG[status], pulse && 'animate-breathe')}
      />
      {label ?? status.toUpperCase()}
    </span>
  );
});
