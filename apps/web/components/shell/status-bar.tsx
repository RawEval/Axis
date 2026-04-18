'use client';

import clsx from 'clsx';
import { useEffect, useState } from 'react';

/**
 * Minimal status bar. Just a dot + "connected / offline". No timestamp,
 * no version, no noise. The user sees it only if they care to look down.
 */
export function StatusBar() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    let cancelled = false;
    const ping = async () => {
      try {
        const res = await fetch(`${base}/healthz`, { cache: 'no-store' });
        if (!cancelled) setOnline(res.ok);
      } catch {
        if (!cancelled) setOnline(false);
      }
    };
    ping();
    const i = setInterval(ping, 30_000);
    return () => {
      cancelled = true;
      clearInterval(i);
    };
  }, []);

  return (
    <footer className="flex h-6 flex-shrink-0 items-center justify-end border-t border-edge bg-canvas-subtle px-4 text-[10px] text-ink-tertiary">
      <span className="flex items-center gap-1.5">
        <span
          className={clsx(
            'h-1.5 w-1.5 rounded-full',
            online ? 'bg-success' : 'bg-danger',
          )}
          aria-hidden
        />
        {online ? 'Connected' : 'Offline'}
      </span>
    </footer>
  );
}
