import type { ReactNode } from 'react';
import { NavRail } from './nav-rail';
import { StatusBar } from './status-bar';
import { TopBar } from './top-bar';

/**
 * Application shell.
 *
 * ┌────────────────────────────────────────────┐
 * │                 TopBar                     │
 * ├────────┬───────────────────────────────────┤
 * │        │                                   │
 * │ NavRail│         Main content              │
 * │        │                                   │
 * ├────────┴───────────────────────────────────┤
 * │                 StatusBar                  │
 * └────────────────────────────────────────────┘
 */
export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <NavRail />
        <main className="min-w-0 flex-1 overflow-y-auto bg-canvas">{children}</main>
      </div>
      <StatusBar />
    </div>
  );
}
