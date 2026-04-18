'use client';

import { useEffect, useState } from 'react';

/**
 * Returns true after the component has mounted on the client.
 *
 * Use this to gate any rendering that depends on browser-only state
 * (localStorage, zustand/persist, React Query caches seeded from storage)
 * to avoid Next.js hydration mismatches.
 *
 *     const mounted = useMounted();
 *     if (!mounted) return <Placeholder />;
 *     return <Actual data={window.localStorage.getItem('…')} />;
 */
export function useMounted() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
