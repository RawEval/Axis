'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  Activity,
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock,
  FolderOpen,
  Home,
  MessageSquare,
  Plug,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const PRIMARY: ReadonlyArray<NavItem> = [
  { href: '/',         label: 'Home',     icon: Home },
  { href: '/chat',     label: 'Chat',     icon: MessageSquare },
  { href: '/feed',     label: 'Activity', icon: Activity },
  { href: '/history',  label: 'History',  icon: Clock },
  { href: '/memory',   label: 'Memory',   icon: Brain },
  { href: '/projects', label: 'Projects', icon: FolderOpen },
];

const SECONDARY: ReadonlyArray<NavItem> = [
  { href: '/connections', label: 'Connections', icon: Plug },
  { href: '/team',        label: 'Team',        icon: Users },
  { href: '/settings',    label: 'Settings',    icon: Settings },
];

const ITEM_BASE =
  'flex items-center gap-3 h-10 px-3 mx-2 my-0.5 rounded-md text-body-s transition-colors duration-[120ms] ease-out';

const ITEM_INACTIVE = 'text-ink-secondary hover:text-ink hover:bg-canvas-elevated';
const ITEM_ACTIVE   = 'text-ink bg-canvas-elevated font-medium';

export function LeftNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string): boolean => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? 'page' : undefined}
        className={clsx(
          ITEM_BASE,
          active ? ITEM_ACTIVE : ITEM_INACTIVE,
          collapsed && 'justify-center px-0',
        )}
        title={collapsed ? item.label : undefined}
      >
        <Icon size={18} aria-hidden="true" className="shrink-0" />
        {!collapsed && <span className="truncate">{item.label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={clsx(
        'flex flex-col bg-canvas-surface border-r border-edge-subtle h-full transition-[width] duration-200 ease-out',
        collapsed ? 'w-14' : 'w-60',
      )}
      aria-label="Primary"
    >
      <div className={clsx('flex items-center h-14 px-4 gap-2 border-b border-edge-subtle', collapsed && 'justify-center px-0')}>
        <span aria-hidden className="block h-3 w-3 rounded-sm bg-accent shrink-0" />
        {!collapsed && <span className="font-display text-heading-2 text-ink">Axis</span>}
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {PRIMARY.map(renderItem)}
        <div className="mx-3 my-2 h-px bg-edge-subtle" aria-hidden="true" />
        {SECONDARY.map(renderItem)}
      </nav>

      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className={clsx(
          'flex items-center gap-2 h-10 px-3 mx-2 my-1 rounded-md text-ink-tertiary hover:text-ink-secondary hover:bg-canvas-elevated transition-colors',
          collapsed && 'justify-center px-0',
        )}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        {!collapsed && <span className="text-caption">Collapse</span>}
      </button>
    </aside>
  );
}
