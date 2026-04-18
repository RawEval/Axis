'use client';

import Link from 'next/link';
import { Button, Field, Input } from '@/components/ui';
import { ExternalLink } from 'lucide-react';

export interface CredentialsPanelProps {
  tool: string;
  toolLabel: string;
}

export function CredentialsPanel({ tool, toolLabel }: CredentialsPanelProps) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-3">
          App credentials
        </h3>
        <p className="text-body-s text-ink-secondary mb-3">
          Using Axis&apos;s default OAuth app. Bring your own to keep your team&apos;s data
          inside your own Workspace app.
        </p>
        <div className="space-y-3">
          <Field label="Client ID">
            <Input placeholder={`${tool}-client-id`} disabled />
          </Field>
          <Field label="Client Secret">
            <Input type="password" placeholder="••••••••" disabled />
          </Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button variant="primary" size="sm" disabled>Use my own app</Button>
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary mb-2">
          Scopes
        </h3>
        <p className="text-body-s text-ink-secondary">
          Granted scopes for {toolLabel}. Detailed scope picker coming soon.
        </p>
      </section>

      <Link
        href="/credentials"
        className="inline-flex items-center gap-2 text-body-s text-accent hover:text-accent-hover"
      >
        Open full credentials page
        <ExternalLink size={12} aria-hidden="true" />
      </Link>
    </div>
  );
}
