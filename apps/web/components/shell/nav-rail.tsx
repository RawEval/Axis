'use client';

import clsx from 'clsx';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/chat', label: 'Ask', icon: '⌘' },
  { href: '/feed', label: 'Activity', icon: '◉' },
  { href: '/history', label: 'History', icon: '↻' },
  { href: '/connections', label: 'Tools', icon: '⚡' },
  { href: '/team', label: 'Team', icon: '◎' },
] as const;

export function NavRail() {
  const pathname = usePathname() ?? '';

  return (
    <aside className="flex w-[52px] flex-shrink-0 flex-col border-r border-edge-onDark bg-nav">
      <nav className="flex flex-1 flex-col items-center gap-1 py-3">
        {NAV.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={clsx(
                'group flex h-9 w-9 items-center justify-center rounded-md text-sm transition-all',
                active
                  ? 'bg-nav-active text-white shadow-sm'
                  : 'text-ink-onDark/60 hover:bg-nav-hover hover:text-white',
              )}
            >
              <span className="text-[15px]">{icon}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
