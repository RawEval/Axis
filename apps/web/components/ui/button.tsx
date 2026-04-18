import clsx from 'clsx';
import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'xs' | 'sm' | 'md';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const BASE =
  'inline-flex items-center justify-center font-medium transition-colors ' +
  'border rounded disabled:opacity-50 disabled:cursor-not-allowed ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1';

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-brand-500 border-brand-500 text-white hover:bg-brand-600 hover:border-brand-600 active:bg-brand-700',
  secondary:
    'bg-canvas-raised border-edge-strong text-ink hover:bg-canvas-subtle active:bg-edge',
  ghost:
    'bg-transparent border-transparent text-ink-secondary hover:bg-canvas-subtle hover:text-ink',
  danger:
    'bg-canvas-raised border-edge-strong text-danger hover:bg-danger-bg hover:border-danger active:bg-danger-bg',
};

const SIZES: Record<Size, string> = {
  xs: 'h-7 px-2.5 text-xs gap-1',
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-9 px-4 text-sm gap-2',
};

export function Button({
  variant = 'primary',
  size = 'sm',
  className,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={clsx(BASE, VARIANTS[variant], SIZES[size], className)}
      {...rest}
    />
  );
}
