import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  children?: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:   'bg-accent text-accent-on hover:bg-accent-hover border-transparent',
  secondary: 'bg-canvas-elevated text-ink border border-edge hover:border-edge-strong hover:bg-canvas-elevated',
  ghost:     'bg-transparent text-ink-secondary hover:text-ink hover:bg-canvas-elevated border-transparent',
  danger:    'bg-danger text-white border-transparent hover:opacity-90',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-body-s gap-1',
  md: 'h-10 px-4 text-body gap-2',
  lg: 'h-12 px-6 text-body-l gap-2',
};

const BASE_CLASSES =
  'inline-flex items-center justify-center rounded-md font-medium transition-colors duration-[120ms] ease-out disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 select-none';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled,
    leadingIcon,
    trailingIcon,
    className,
    children,
    type = 'button',
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={clsx(BASE_CLASSES, VARIANT_CLASSES[variant], SIZE_CLASSES[size], className)}
      {...rest}
    >
      {leadingIcon}
      {loading ? (
        <span className="inline-block h-3 w-3 rounded-full border-2 border-current border-r-transparent animate-spin" />
      ) : (
        children
      )}
      {trailingIcon}
    </button>
  );
});
