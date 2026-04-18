import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type AvatarShape = 'circle' | 'agent';
export type AvatarSize = 'sm' | 'md' | 'lg';

export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  name?: string;
  src?: string;
  alt?: string;
  shape?: AvatarShape;
  size?: AvatarSize;
}

const SIZE_CLASSES: Record<AvatarSize, string> = {
  sm: 'h-6 w-6 text-caption',
  md: 'h-8 w-8 text-body-s',
  lg: 'h-10 w-10 text-body',
};

const SHAPE_CLASSES: Record<AvatarShape, string> = {
  circle: 'rounded-full',
  agent: 'rounded-md',
};

function initial(name?: string): string {
  if (!name) return '?';
  const c = name.trim().charAt(0);
  return c ? c.toUpperCase() : '?';
}

export const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(function Avatar(
  { name, src, alt, shape = 'circle', size = 'md', className, ...rest },
  ref,
) {
  const base = clsx(
    'inline-flex items-center justify-center font-medium overflow-hidden border border-edge-subtle bg-canvas-elevated text-ink',
    SIZE_CLASSES[size],
    SHAPE_CLASSES[shape],
    className,
  );

  return (
    <span ref={ref} className={base} {...rest}>
      {src ? (
        <img src={src} alt={alt ?? name ?? ''} className="h-full w-full object-cover" />
      ) : (
        initial(name)
      )}
    </span>
  );
});
