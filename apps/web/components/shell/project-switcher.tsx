'use client';

import clsx from 'clsx';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Badge, Button, Modal } from '@/components/ui';
import { useProjectStore } from '@/lib/project-store';
import { type Project, useProjects } from '@/lib/queries/projects';

/**
 * Project switcher.
 *
 * Opens from the top-bar project button. Shows the user's projects as a
 * clean list (no cryptic "All / Auto" dropdown). Clicking a project makes
 * it active and closes the modal. A "query across all projects" toggle is
 * only surfaced when the user has 2+ projects.
 */
export function ProjectSwitcher({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { data: projects, isLoading } = useProjects();
  const active = useProjectStore((s) => s.activeProject);
  const setActive = useProjectStore((s) => s.setActiveProject);

  const pick = (value: string) => {
    setActive(value);
    onClose();
  };

  const hasMultiple = (projects?.length ?? 0) > 1;

  return (
    <Modal open={open} onClose={onClose} title="Switch project" widthClass="max-w-sm">
      <div className="p-2">
        {isLoading && (
          <div className="px-3 py-4 text-sm text-ink-tertiary">Loading projects…</div>
        )}

        {projects && projects.length > 0 && (
          <ul className="space-y-0.5">
            {projects.map((p) => (
              <ProjectRow
                key={p.id}
                project={p}
                active={active === p.id || (!active && p.is_default)}
                onSelect={() => pick(p.id)}
              />
            ))}
          </ul>
        )}

        {hasMultiple && (
          <div className="mt-2 border-t border-edge-subtle px-3 pt-3">
            <div className="label-caps mb-2">Cross-project</div>
            <button
              type="button"
              onClick={() => pick('all')}
              className={clsx(
                'w-full rounded px-3 py-2 text-left text-sm transition-colors',
                active === 'all'
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-ink-secondary hover:bg-canvas-subtle',
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">Query across all projects</span>
                {active === 'all' && <Badge tone="brand">active</Badge>}
              </div>
              <div className="mt-0.5 text-xs text-ink-tertiary">
                Agent runs fan out across every project and merge results.
              </div>
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-edge bg-canvas-subtle px-5 py-3">
        <span className="text-xs text-ink-tertiary">
          {projects?.length ?? 0} {projects?.length === 1 ? 'project' : 'projects'}
        </span>
        <Button
          size="xs"
          variant="secondary"
          onClick={() => {
            onClose();
            router.push('/projects/new');
          }}
        >
          New project
        </Button>
      </div>
    </Modal>
  );
}

function ProjectRow({
  project,
  active,
  onSelect,
}: {
  project: Project;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={clsx(
          'w-full rounded px-3 py-2 text-left transition-colors',
          active
            ? 'bg-brand-50 text-brand-700'
            : 'text-ink hover:bg-canvas-subtle',
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium">{project.name}</span>
              {project.is_default && <Badge tone="neutral">default</Badge>}
            </div>
            {project.description && (
              <div className="mt-0.5 truncate text-xs text-ink-tertiary">
                {project.description}
              </div>
            )}
          </div>
          {active && <Badge tone="brand">active</Badge>}
        </div>
      </button>
    </li>
  );
}
