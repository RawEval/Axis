import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

/** A standard bordered panel — the default container for content blocks. */
export function Panel({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx('rounded-md border border-edge bg-canvas-raised shadow-panel', className)}
      {...rest}
    />
  );
}

export function PanelHeader({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'flex items-center justify-between border-b border-edge px-5 py-3',
        className,
      )}
      {...rest}
    />
  );
}

export function PanelBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx('px-5 py-4', className)} {...rest} />;
}

export function PanelFooter({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'flex items-center justify-end gap-2 border-t border-edge bg-canvas-subtle px-5 py-3',
        className,
      )}
      {...rest}
    />
  );
}
