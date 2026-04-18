import clsx from 'clsx';
import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react';

/**
 * Data table primitives. Modeled after Tableau/Retool admin tables:
 * - dense rows
 * - zebra stripes
 * - sticky header
 * - tabular numerals
 */

export function Table({ className, ...rest }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-hidden rounded-md border border-edge bg-canvas-raised shadow-panel">
      <table className={clsx('w-full text-left text-sm text-ink', className)} {...rest} />
    </div>
  );
}

export function THead({ className, ...rest }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={clsx('border-b border-edge bg-canvas-subtle text-ink-secondary', className)}
      {...rest}
    />
  );
}

export function TBody({ className, ...rest }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={clsx('divide-y divide-edge-subtle', className)} {...rest} />;
}

export function TR({
  className,
  interactive = false,
  ...rest
}: HTMLAttributes<HTMLTableRowElement> & { interactive?: boolean }) {
  return (
    <tr
      className={clsx(interactive && 'row-hover cursor-pointer', className)}
      {...rest}
    />
  );
}

export function TH({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={clsx(
        'px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-ink-tertiary',
        className,
      )}
      {...rest}
    />
  );
}

export function TD({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={clsx('px-4 py-3', className)} {...rest} />;
}
