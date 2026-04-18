import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'brand';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  dot?: boolean;
}

const TONES: Record<Tone, string> = {
  neutral: 'bg-canvas-subtle border-edge text-ink-secondary',
  info: 'bg-info-bg border-info/20 text-info-fg',
  success: 'bg-success-bg border-success/20 text-success-fg',
  warning: 'bg-warning-bg border-warning/30 text-warning-fg',
  danger: 'bg-danger-bg border-danger/20 text-danger-fg',
  brand: 'bg-brand-50 border-brand-200 text-brand-700',
};

const DOT_TONES: Record<Tone, string> = {
  neutral: 'bg-ink-tertiary',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  brand: 'bg-brand-500',
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
