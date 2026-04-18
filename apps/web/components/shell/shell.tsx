'use client';

import { type ReactNode } from 'react';
import { ToastViewport, TooltipProvider } from '@axis/design-system';
import { LeftNav } from './left-nav';
import { TopBar } from './top-bar';
import { RightPanel } from './right-panel';
import { CommandPalette } from './command-palette';
import { ShortcutOverlay } from './shortcut-overlay';
import { useGlobalShortcuts } from '@/lib/global-shortcuts';

export function Shell({ children }: { children: ReactNode }) {
  useGlobalShortcuts();
  return (
    <TooltipProvider delayDuration={500}>
      <div className="flex h-screen w-screen overflow-hidden bg-canvas">
        <LeftNav />
        <div className="flex flex-1 min-w-0 flex-col">
          <TopBar />
          <div className="flex flex-1 min-h-0">
            <main className="flex-1 overflow-y-auto">{children}</main>
            <RightPanel />
          </div>
        </div>
      </div>
      <CommandPalette />
      <ShortcutOverlay />
      <ToastViewport />
    </TooltipProvider>
  );
}
