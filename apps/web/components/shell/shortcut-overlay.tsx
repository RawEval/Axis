'use client';

import { X } from 'lucide-react';
import { Kbd } from '@axis/design-system';
import { shortcutOverlay, useShortcutOverlay } from '@/lib/global-shortcuts';

interface Shortcut {
  keys: ReadonlyArray<string>;
  label: string;
}

interface ShortcutGroup {
  title: string;
  items: ReadonlyArray<Shortcut>;
}

const GROUPS: ReadonlyArray<ShortcutGroup> = [
  {
    title: 'Global',
    items: [
      { keys: ['⌘', 'K'],          label: 'Command palette' },
      { keys: ['?'],                label: 'Show shortcuts' },
      { keys: ['Esc'],              label: 'Close palette / overlay' },
    ],
  },
  {
    title: 'Navigation',
    items: [
      { keys: ['G', 'H'],           label: 'Go to Home' },
      { keys: ['G', 'C'],           label: 'Go to Chat' },
      { keys: ['G', 'A'],           label: 'Go to Activity' },
      { keys: ['G', 'S'],           label: 'Go to Settings' },
    ],
  },
  {
    title: 'Chat (coming soon)',
    items: [
      { keys: ['⌘', '⏎'],          label: 'Send prompt' },
      { keys: ['⇧', '⏎'],          label: 'Newline' },
      { keys: ['⌘', '.'],           label: 'Stop current run' },
    ],
  },
];

export function ShortcutOverlay() {
  const { open } = useShortcutOverlay();
  if (!open) return null;

  const close = () => shortcutOverlay.close();

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 backdrop-blur-[2px]"
      onClick={close}
    >
      <div
        role="dialog"
        aria-label="Keyboard shortcuts"
        className="w-full max-w-[640px] mx-4 max-h-[80vh] bg-canvas-surface border border-edge rounded-lg shadow-e3 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between h-12 px-4 border-b border-edge-subtle">
          <h2 className="font-display text-heading-2 text-ink">Keyboard shortcuts</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={close}
            className="inline-flex items-center justify-center h-8 w-8 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {GROUPS.map((group) => (
            <section key={group.title}>
              <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-3">
                {group.title}
              </h3>
              <ul className="space-y-2">
                {group.items.map((s) => (
                  <li key={s.label} className="flex items-center justify-between text-body-s">
                    <span className="text-ink">{s.label}</span>
                    <span className="flex items-center gap-1">
                      {s.keys.map((k) => (
                        <Kbd key={k}>{k}</Kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
