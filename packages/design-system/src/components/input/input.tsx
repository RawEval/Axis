import { forwardRef, type InputHTMLAttributes } from 'react';
import clsx from 'clsx';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  invalid?: boolean;
}

const BASE_CLASSES =
  'block w-full h-10 px-3 py-2 rounded-md text-body bg-canvas-surface text-ink placeholder:text-ink-tertiary border border-edge transition-colors duration-[120ms] ease-out focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-50 disabled:cursor-not-allowed';

const ERROR_CLASSES = 'border-danger focus:border-danger focus:ring-danger/20';

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={clsx(BASE_CLASSES, invalid && ERROR_CLASSES, className)}
      {...rest}
    />
  );
});
