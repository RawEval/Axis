import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'brand';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  dot?: boolean;
}

const TONES: Record<Tone, string> = {
  neutral: 'bg-canvas-elevated border-edge text-ink-secondary',
  info: 'bg-info/10 border-info/20 text-info',
  success: 'bg-success/10 border-success/20 text-success',
  warning: 'bg-warning/10 border-warning/30 text-warning',
  danger: 'bg-danger/10 border-danger/20 text-danger',
  brand: 'bg-accent-subtle border-accent-subtle text-accent',
};

const DOT_TONES: Record<Tone, string> = {
  neutral: 'bg-ink-tertiary',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  brand: 'bg-accent',
};

export function Badge({ tone = 'neutral', dot, className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        TONES[tone],
        className,
      )}
      {...rest}
    >
      {dot && <span className={clsx('h-1.5 w-1.5 rounded-full', DOT_TONES[tone])} />}
      {children}
    </span>
  );
}
