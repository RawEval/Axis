'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import {
  Button,
  Field,
  Input,
  PageHeader,
  Panel,
  PanelBody,
  PanelFooter,
  Textarea,
} from '@/components/ui';
import { ApiError } from '@/lib/api';
import { useProjectStore } from '@/lib/project-store';
import { useCreateProject } from '@/lib/queries/projects';

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const setActive = useProjectStore((s) => s.setActiveProject);
  const create = useCreateProject();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const project = await create.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setActive(project.id);
      router.push('/connections');
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'create failed'
          : 'create failed',
      );
    }
  };

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-5 px-6 py-6">
      <PageHeader title="New project" />

      <Panel>
        <form onSubmit={onSubmit}>
          <PanelBody className="space-y-4">
            <Field label="Name" required>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                required
                autoFocus
                placeholder="e.g. Acme Engagement, Internal Ops"
              />
            </Field>
            <Field
              label="Description"
              hint="What lives in this project? Which tools? Which people? This text helps the auto-classifier route prompts later."
            >
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                maxLength={2000}
              />
            </Field>
            {error && (
              <div className="rounded border border-danger/20 bg-danger-bg px-3 py-2 text-xs text-danger-fg">
                {error}
              </div>
            )}
          </PanelBody>
          <PanelFooter>
            <Button variant="ghost" size="sm" type="button" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={create.isPending || !name.trim()}>
              {create.isPending ? 'Creating…' : 'Create project'}
            </Button>
          </PanelFooter>
        </form>
      </Panel>
    </div>
  );
}
