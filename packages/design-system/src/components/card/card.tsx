import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

const CARD_BASE = 'bg-canvas-surface border border-edge-subtle rounded-lg overflow-hidden';

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx(CARD_BASE, className)} {...rest}>
      {children}
    </div>
  );
});

export const CardHeader = forwardRef<HTMLDivElement, CardProps>(function CardHeader(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4 border-b border-edge-subtle', className)} {...rest}>
      {children}
    </div>
  );
});

export const CardBody = forwardRef<HTMLDivElement, CardProps>(function CardBody(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4', className)} {...rest}>
      {children}
    </div>
  );
});

export const CardFooter = forwardRef<HTMLDivElement, CardProps>(function CardFooter(
  { className, children, ...rest },
  ref,
) {
  return (
    <div ref={ref} className={clsx('px-5 py-4 border-t border-edge-subtle', className)} {...rest}>
      {children}
    </div>
  );
});
