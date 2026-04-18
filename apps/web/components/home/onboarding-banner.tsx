'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Plug, X, MessageSquare } from 'lucide-react';

const STORAGE_KEY = 'axis.onboarded';

export function OnboardingBanner() {
  const [visible, setVisible] = useState<boolean | null>(null);

  useEffect(() => {
    setVisible(window.localStorage.getItem(STORAGE_KEY) !== 'true');
  }, []);

  const dismiss = () => {
    window.localStorage.setItem(STORAGE_KEY, 'true');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <aside
      role="region"
      aria-label="Welcome to Axis"
      className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-lg border border-accent/30 bg-accent-subtle px-5 py-4"
    >
      <div className="space-y-1">
        <h2 className="font-display text-heading-2 text-ink">Welcome to Axis</h2>
        <p className="text-body-s text-ink-secondary">
          Connect a tool, then ask Axis to do something across your work.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Link
          href="/connections"
          className="inline-flex items-center gap-2 h-8 px-3 rounded-md bg-accent text-accent-on text-body-s font-medium hover:bg-accent-hover transition-colors"
        >
          <Plug size={14} aria-hidden="true" />
          Connect a tool
        </Link>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 h-8 px-3 rounded-md text-body-s text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors"
        >
          <MessageSquare size={14} aria-hidden="true" />
          Start a chat
        </Link>
      </div>
      <button
        type="button"
        aria-label="Dismiss welcome banner"
        onClick={dismiss}
        className="absolute top-2 right-2 inline-flex items-center justify-center h-7 w-7 rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-elevated transition-colors"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </aside>
  );
}
