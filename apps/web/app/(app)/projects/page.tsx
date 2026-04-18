'use client';

import Link from 'next/link';
import { useState } from 'react';
import { FolderOpen, Plus } from 'lucide-react';
import { Card, CardBody, Input } from '@axis/design-system';
import { useProjects } from '@/lib/queries/projects';
import { useMounted } from '@/lib/use-mounted';

export default function ProjectsPage() {
  const mounted = useMounted();
  const { data: rawProjects } = useProjects();
  const projects = mounted ? rawProjects ?? [] : [];

  const [query, setQuery] = useState('');
  const filtered = query
    ? projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
    : projects;

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-8 px-12 py-10">
      <header className="flex items-center justify-between">
        <h1 className="font-display text-display-l text-ink">Projects</h1>
        <Link
          href="/projects/new"
          className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-4 text-body-s font-medium text-accent-on transition-colors hover:bg-accent-hover"
        >
          <Plus size={14} aria-hidden="true" />
          New project
        </Link>
      </header>

      <Input
        placeholder="Search projects…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-edge-subtle py-20">
          <FolderOpen size={36} className="text-ink-tertiary" aria-hidden="true" />
          <div className="space-y-1 text-center">
            <p className="font-display text-heading-1 text-ink">
              {query ? 'No matching projects' : 'No projects yet'}
            </p>
            <p className="text-body-s text-ink-tertiary">
              {query
                ? 'Try a different search term.'
                : 'Projects group related runs, memories, and connections.'}
            </p>
          </div>
          {!query && (
            <Link
              href="/projects/new"
              className="inline-flex h-8 items-center gap-2 rounded-md bg-accent px-4 text-body-s font-medium text-accent-on transition-colors hover:bg-accent-hover"
            >
              <Plus size={14} aria-hidden="true" />
              New project
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <Card key={p.id} className="transition-colors hover:border-edge-strong">
              <CardBody className="space-y-2">
                <div className="text-body-l font-medium text-ink">{p.name}</div>
                <div className="text-body-s text-ink-secondary">
                  {p.description ?? 'No description'}
                </div>
                <div className="font-mono text-caption tabular-nums text-ink-tertiary">
                  Updated {new Date(p.updated_at).toLocaleDateString()}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
