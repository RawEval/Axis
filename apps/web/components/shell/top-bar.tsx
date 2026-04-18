'use client';

import { LogOut, User } from 'lucide-react';
import {
  Avatar,
  Kbd,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@axis/design-system';
import { ThemeToggle } from './theme-toggle';
import { commandPalette } from '@/lib/global-shortcuts';

export function TopBar() {
  return (
    <header
      className="flex items-center h-12 px-4 border-b border-edge-subtle bg-canvas-surface gap-4"
      role="banner"
    >
      <div className="flex-1" />

      <button
        type="button"
        aria-label="Open command palette"
        onClick={() => commandPalette.open()}
        className="inline-flex items-center gap-2 h-8 px-3 rounded-md border border-edge text-ink-secondary hover:text-ink hover:bg-canvas-elevated text-body-s transition-colors"
      >
        <span>Search…</span>
        <Kbd>⌘K</Kbd>
      </button>

      <div className="flex-1 flex items-center justify-end gap-1">
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Account menu"
            className="inline-flex items-center justify-center h-8 w-8 rounded-full hover:bg-canvas-elevated transition-colors"
          >
            <Avatar name="A" size="sm" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Account</DropdownMenuLabel>
            <DropdownMenuItem>
              <User size={14} aria-hidden="true" className="mr-2" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-danger data-[highlighted]:text-danger">
              <LogOut size={14} aria-hidden="true" className="mr-2" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
