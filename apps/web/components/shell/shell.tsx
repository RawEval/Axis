'use client';

import { type ReactNode } from 'react';
import { ToastViewport, TooltipProvider } from '@axis/design-system';
import { LeftNav } from './left-nav';
import { TopBar } from './top-bar';
import { RightPanel } from './right-panel';

export function Shell({ children }: { children: ReactNode }) {
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
      <ToastViewport />
    </TooltipProvider>
  );
}
