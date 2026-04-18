'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { clearToken } from '@/lib/auth';
import { useMe } from '@/lib/queries/auth';
import { useMounted } from '@/lib/use-mounted';

/**
 * User menu. Click the avatar in the top-right to open a dropdown with
 * user-level routes (Credentials, Memory, Settings) + Sign out.
 *
 * These are intentionally NOT in the main left nav — the left nav is
 * project-scoped work, the user menu is personal account stuff.
 */
export function UserMenu() {
  const mounted = useMounted();
  const { data: me } = useMe();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // Server render always uses the neutral placeholder — avoids hydration
  // mismatch with localStorage-backed user cache.
  const initial = mounted
    ? (me?.name ?? me?.email ?? '?').charAt(0).toUpperCase()
    : '\u00A0'; // &nbsp; — same character width, no visible mismatch

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-edge-strong bg-canvas-raised text-xs font-semibold text-ink-secondary transition-colors hover:border-brand-500 hover:text-ink"
      >
        {initial}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-40 mt-1.5 w-60 rounded-md border border-edge bg-canvas-raised py-1 shadow-popover"
        >
          <div className="border-b border-edge-subtle px-4 py-2.5">
            <div className="truncate text-sm font-medium text-ink">
              {me?.name ?? 'Unnamed user'}
            </div>
            <div className="truncate text-xs text-ink-tertiary">{me?.email ?? '—'}</div>
            <div className="mt-1 inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-ink-tertiary">
              Plan · <span className="text-ink-secondary">{me?.plan ?? 'free'}</span>
            </div>
          </div>
          <MenuLink href="/credentials" onSelect={() => setOpen(false)}>
            Credentials
          </MenuLink>
          <MenuLink href="/memory" onSelect={() => setOpen(false)}>
            Memory
          </MenuLink>
          <MenuLink href="/settings" onSelect={() => setOpen(false)}>
            Settings
          </MenuLink>
          <div className="my-1 border-t border-edge-subtle" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              clearToken();
              if (typeof window !== 'undefined') window.location.href = '/login';
            }}
            className="block w-full px-4 py-1.5 text-left text-sm text-ink-secondary hover:bg-canvas-subtle hover:text-ink"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function MenuLink({
  href,
  onSelect,
  children,
}: {
  href: string;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      role="menuitem"
      onClick={onSelect}
      className="block px-4 py-1.5 text-sm text-ink-secondary hover:bg-canvas-subtle hover:text-ink"
    >
      {children}
    </Link>
  );
}
