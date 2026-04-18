import clsx from 'clsx';
import type {
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from 'react';

export { Input, type InputProps } from '@axis/design-system';

const FIELD_CLS =
  'w-full rounded border border-edge-strong bg-canvas-surface px-3 py-2 text-sm text-ink ' +
  'placeholder:text-ink-tertiary transition-colors ' +
  'hover:border-ink-tertiary ' +
  'focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent ' +
  'disabled:cursor-not-allowed disabled:bg-canvas-elevated disabled:text-ink-tertiary';

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={clsx(FIELD_CLS, 'resize-y', className)} {...rest} />;
}

export function Select({
  className,
  children,
  ...rest
}: InputHTMLAttributes<HTMLSelectElement> & { children?: ReactNode }) {
  return (
    <select className={clsx(FIELD_CLS, 'pr-8', className)} {...rest}>
      {children}
    </select>
  );
}

export function Label({
  className,
  required,
  children,
  ...rest
}: LabelHTMLAttributes<HTMLLabelElement> & { required?: boolean }) {
  return (
    <label
      className={clsx('mb-1 block text-xs font-medium text-ink-secondary', className)}
      {...rest}
    >
      {children}
      {required && <span className="ml-0.5 text-danger">*</span>}
    </label>
  );
}

export function Field({
  label,
  hint,
  error,
  required,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <Label required={required}>{label}</Label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-ink-tertiary">{hint}</p>}
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}
