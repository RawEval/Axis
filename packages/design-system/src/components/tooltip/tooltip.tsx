'use client';

import * as TT from '@radix-ui/react-tooltip';
import clsx from 'clsx';
import { type ReactNode } from 'react';

export const TooltipProvider = TT.Provider;

export interface TooltipProps {
  label: ReactNode;
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  delayDuration?: number;
}

const CONTENT =
  'z-[70] px-2 py-1 rounded bg-canvas-surface border border-edge shadow-e2 text-caption text-ink-secondary';

export function Tooltip({
  label,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 600,
}: TooltipProps) {
  return (
    <TT.Root delayDuration={delayDuration}>
      <TT.Trigger asChild>{children}</TT.Trigger>
      <TT.Portal>
        <TT.Content side={side} align={align} className={clsx(CONTENT)} sideOffset={4}>
          {label}
        </TT.Content>
      </TT.Portal>
    </TT.Root>
  );
}
