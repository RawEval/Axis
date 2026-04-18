import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'rounded-card border border-white/5 bg-bg-elevated/80 p-5 backdrop-blur-md',
        className,
      )}
      {...rest}
    />
  );
}
