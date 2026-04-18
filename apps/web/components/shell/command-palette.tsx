'use client';

import { Command } from 'cmdk';
import { useRouter } from 'next/navigation';
import {
  Activity,
  Brain,
  Clock,
  FolderOpen,
  Home,
  MessageSquare,
  Monitor,
  Moon,
  Plug,
  Settings,
  Sun,
  Users,
} from 'lucide-react';
import { commandPalette, useCommandPalette } from '@/lib/global-shortcuts';
import { useTheme, type Theme } from '@/lib/theme';

const NAV = [
  { href: '/',            label: 'Home',        icon: Home },
  { href: '/chat',        label: 'Chat',        icon: MessageSquare },
  { href: '/feed',        label: 'Activity',    icon: Activity },
  { href: '/history',     label: 'History',     icon: Clock },
  { href: '/memory',      label: 'Memory',      icon: Brain },
  { href: '/projects',    label: 'Projects',    icon: FolderOpen },
  { href: '/connections', label: 'Connections', icon: Plug },
  { href: '/team',        label: 'Team',        icon: Users },
  { href: '/settings',    label: 'Settings',    icon: Settings },
] as const;

const THEMES: ReadonlyArray<{ value: Theme; label: string; Icon: typeof Sun }> = [
  { value: 'system', label: 'Use system theme', Icon: Monitor },
  { value: 'light',  label: 'Light theme',      Icon: Sun },
  { value: 'dark',   label: 'Dark theme',       Icon: Moon },
];

export function CommandPalette() {
  const { open } = useCommandPalette();
  const router = useRouter();
  const { setTheme } = useTheme();

  if (!open) return null;

  const close = () => commandPalette.close();

  return (
    <div
      className="fixed inset-0 z-[80] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-[2px]"
      onClick={close}
    >
      <Command
        label="Command palette"
        className="w-full max-w-[520px] mx-4 bg-canvas-surface border border-edge rounded-lg shadow-e3 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command.Input
          placeholder="Search…"
          autoFocus
          className="w-full h-12 px-4 bg-transparent border-b border-edge-subtle text-body text-ink placeholder:text-ink-tertiary focus:outline-none"
        />
        <Command.List className="max-h-[60vh] overflow-y-auto p-2">
          <Command.Empty className="px-4 py-6 text-center text-body-s text-ink-tertiary">
            No results.
          </Command.Empty>

          <Command.Group
            heading="Navigation"
            className="text-ink-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em]"
          >
            {NAV.map((item) => {
              const Icon = item.icon;
              return (
                <Command.Item
                  key={item.href}
                  value={`nav-${item.label}`}
                  onSelect={() => {
                    router.push(item.href);
                    close();
                  }}
                  className="flex items-center gap-3 h-9 px-2 rounded-sm text-body-s text-ink-secondary cursor-pointer data-[selected=true]:bg-canvas-elevated data-[selected=true]:text-ink"
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{item.label}</span>
                </Command.Item>
              );
            })}
          </Command.Group>

          <Command.Group
            heading="Theme"
            className="text-ink-tertiary [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em]"
          >
            {THEMES.map(({ value, label, Icon }) => (
              <Command.Item
                key={value}
                value={`theme-${value}`}
                onSelect={() => {
                  setTheme(value);
                  close();
                }}
                className="flex items-center gap-3 h-9 px-2 rounded-sm text-body-s text-ink-secondary cursor-pointer data-[selected=true]:bg-canvas-elevated data-[selected=true]:text-ink"
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
