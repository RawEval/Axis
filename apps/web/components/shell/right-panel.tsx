'use client';

import { X } from 'lucide-react';
import { useEffect } from 'react';
import { rightPanel, useRightPanel } from '@/lib/right-panel';

export function RightPanel() {
  const state = useRightPanel();

  useEffect(() => {
    if (!state.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') rightPanel.close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [state.open]);

  if (!state.open) return null;

  return (
    <aside
      role="complementary"
      aria-label={state.title}
      className="w-[360px] flex-shrink-0 border-l border-edge-subtle bg-canvas-surface flex flex-col h-full"
    >
      <div className="flex items-center justify-between h-12 px-4 border-b border-edge-subtle">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-secondary truncate">
          {state.title}
        </h2>
        <button
          type="button"
          aria-label="Close panel"
          onClick={() => rightPanel.close()}
          className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated transition-colors"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 text-body-s text-ink">{state.body}</div>
    </aside>
  );
}
