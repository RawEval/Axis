'use client';

import { Monitor, Moon, Sun } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@axis/design-system';
import { useTheme, type Theme } from '@/lib/theme';

const ICON: Record<Theme, typeof Monitor> = {
  system: Monitor,
  light: Sun,
  dark: Moon,
};

const LABEL: Record<Theme, string> = {
  system: 'System',
  light: 'Light',
  dark: 'Dark',
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Icon = ICON[theme];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Theme: ${LABEL[theme]}`}
        className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
      >
        <Icon size={16} aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(['system', 'light', 'dark'] as const).map((t) => {
          const ItemIcon = ICON[t];
          return (
            <DropdownMenuItem key={t} onSelect={() => setTheme(t)}>
              <ItemIcon size={14} aria-hidden="true" className="mr-2" />
              <span>{LABEL[t]}</span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
