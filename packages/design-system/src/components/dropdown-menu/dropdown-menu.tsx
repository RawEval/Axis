'use client';

import * as DM from '@radix-ui/react-dropdown-menu';
import clsx from 'clsx';
import { forwardRef, type ComponentPropsWithoutRef } from 'react';

export const DropdownMenu = DM.Root;
export const DropdownMenuTrigger = DM.Trigger;

const CONTENT =
  'min-w-[180px] z-50 bg-canvas-surface border border-edge rounded-md shadow-e2 p-1 outline-none';

export const DropdownMenuContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Content>
>(function DropdownMenuContent({ className, sideOffset = 4, ...rest }, ref) {
  return (
    <DM.Portal>
      <DM.Content
        ref={ref}
        sideOffset={sideOffset}
        className={clsx(CONTENT, className)}
        {...rest}
      />
    </DM.Portal>
  );
});

const ITEM =
  'relative flex items-center h-8 px-3 rounded-sm text-body-s text-ink-secondary cursor-pointer outline-none data-[highlighted]:bg-canvas-elevated data-[highlighted]:text-ink data-[disabled]:opacity-40 data-[disabled]:cursor-not-allowed';

export const DropdownMenuItem = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Item>
>(function DropdownMenuItem({ className, ...rest }, ref) {
  return <DM.Item ref={ref} className={clsx(ITEM, className)} {...rest} />;
});

export const DropdownMenuSeparator = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Separator>
>(function DropdownMenuSeparator({ className, ...rest }, ref) {
  return (
    <DM.Separator
      ref={ref}
      className={clsx('h-px my-1 bg-edge-subtle', className)}
      {...rest}
    />
  );
});

export const DropdownMenuLabel = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof DM.Label>
>(function DropdownMenuLabel({ className, ...rest }, ref) {
  return (
    <DM.Label
      ref={ref}
      className={clsx(
        'px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.04em] text-ink-tertiary',
        className,
      )}
      {...rest}
    />
  );
});
