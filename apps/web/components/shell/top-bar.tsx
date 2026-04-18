'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useProjectStore } from '@/lib/project-store';
import { useProjects } from '@/lib/queries/projects';
import { useMounted } from '@/lib/use-mounted';
import { ProjectSwitcher } from './project-switcher';
import { UserMenu } from './user-menu';

export function TopBar() {
  const [switcherOpen, setSwitcherOpen] = useState(false);

  return (
    <header className="flex h-11 flex-shrink-0 items-center justify-between border-b border-edge bg-canvas-raised px-3">
      <div className="flex items-center gap-2">
        <Link href="/chat" className="flex items-center gap-1.5 text-ink">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-brand-500 text-[10px] font-bold text-white">A</span>
          <span className="text-sm font-semibold tracking-tight">Axis</span>
        </Link>
        <span className="text-edge-strong">/</span>
        <ProjectButton onClick={() => setSwitcherOpen(true)} />
      </div>
      <UserMenu />
      <ProjectSwitcher open={switcherOpen} onClose={() => setSwitcherOpen(false)} />
    </header>
  );
}

function ProjectButton({ onClick }: { onClick: () => void }) {
  const mounted = useMounted();
  const { data: projects } = useProjects();
  const active = useProjectStore((s) => s.activeProject);

  let label = 'Project';
  if (mounted) {
    if (active === 'all') label = 'All projects';
    else if (!active || active === 'auto') label = projects?.find((p) => p.is_default)?.name ?? 'Project';
    else label = projects?.find((p) => p.id === active)?.name ?? 'Project';
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1 rounded px-1.5 py-0.5 text-sm text-ink-secondary transition-colors hover:bg-canvas-subtle hover:text-ink"
    >
      <span suppressHydrationWarning>{label}</span>
      <svg aria-hidden width="10" height="10" viewBox="0 0 12 12" fill="none" className="text-ink-tertiary">
        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
