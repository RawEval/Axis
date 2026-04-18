import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface KbdProps extends HTMLAttributes<HTMLElement> {
  children?: ReactNode;
}

const BASE =
  'inline-flex items-center justify-center min-w-[20px] h-[20px] px-1 rounded-xs border border-edge bg-canvas-elevated text-ink-secondary font-mono text-[11px] tracking-[0.02em] tabular-nums';

export const Kbd = forwardRef<HTMLElement, KbdProps>(function Kbd(
  { className, children, ...rest },
  ref,
) {
  return (
    <kbd ref={ref} className={clsx(BASE, className)} {...rest}>
      {children}
    </kbd>
  );
});
