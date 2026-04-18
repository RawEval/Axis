import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type SkeletonRounded = 'sm' | 'md' | 'lg' | 'full';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: number | string;
  height?: number | string;
  rounded?: SkeletonRounded;
}

const ROUNDED: Record<SkeletonRounded, string> = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

const BASE = 'block bg-canvas-elevated overflow-hidden relative animate-shimmer';

function px(v: number | string | undefined): string | undefined {
  if (v == null) return undefined;
  return typeof v === 'number' ? `${v}px` : v;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(function Skeleton(
  { width, height, rounded = 'md', className, style, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      aria-hidden="true"
      className={clsx(BASE, ROUNDED[rounded], className)}
      style={{ width: px(width), height: px(height), ...style }}
      {...rest}
    />
  );
});
