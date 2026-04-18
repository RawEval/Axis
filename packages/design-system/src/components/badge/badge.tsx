import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  dot?: boolean;
  children?: ReactNode;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: 'bg-canvas-elevated text-ink-secondary border-edge-subtle',
  accent:  'bg-accent-subtle text-accent border-accent/30',
  success: 'bg-success/10 text-success border-success/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
  danger:  'bg-danger/10 text-danger border-danger/30',
  info:    'bg-info/10 text-info border-info/30',
};

const DOT_COLOR: Record<BadgeTone, string> = {
  neutral: 'bg-ink-tertiary',
  accent:  'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger:  'bg-danger',
  info:    'bg-info',
};

const BASE = 'inline-flex items-center gap-1.5 h-5 px-2 rounded-full border text-caption font-medium tabular-nums';

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { tone = 'neutral', dot = false, className, children, ...rest },
  ref,
) {
  return (
    <span ref={ref} className={clsx(BASE, TONE_CLASSES[tone], className)} {...rest}>
      {dot && <span aria-hidden="true" className={clsx('h-1.5 w-1.5 rounded-full', DOT_COLOR[tone])} />}
      {children}
    </span>
  );
});
