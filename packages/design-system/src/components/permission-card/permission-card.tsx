'use client';

import clsx from 'clsx';
import { type ReactNode } from 'react';
import { Card, CardHeader, CardBody, CardFooter } from '../card';
import { Button } from '../button';

export type PermissionLifetime = 'session' | 'project' | '24h' | 'forever';
export type PermissionDecision = PermissionLifetime | 'deny';

export interface PermissionCardProps {
  capability: string;
  description: ReactNode;
  inputs?: Record<string, unknown>;
  busy?: PermissionDecision | null;
  onAllow: (lifetime: PermissionLifetime) => void;
  onDeny: () => void;
  className?: string;
}

const LIFETIME_LABELS: Record<PermissionLifetime, { label: string; hint: string }> = {
  session: { label: 'Allow once',         hint: 'just this call' },
  project: { label: 'Allow for project',  hint: 'remember for this project' },
  '24h':   { label: 'Allow 24h',          hint: 're-ask tomorrow' },
  forever: { label: 'Allow forever',      hint: 'across all sessions' },
};

const ORDER: PermissionLifetime[] = ['session', 'project', '24h', 'forever'];

export function PermissionCard({
  capability,
  description,
  inputs,
  busy,
  onAllow,
  onDeny,
  className,
}: PermissionCardProps) {
  return (
    <Card className={clsx('shadow-e1', className)}>
      <CardHeader className="flex items-start gap-2">
        <span aria-hidden className="mt-1 inline-block h-2 w-2 rounded-full bg-agent-awaiting animate-breathe" />
        <div>
          <div className="text-body-s text-ink">
            Axis wants to use <span className="font-mono text-mono-s">{capability}</span>
          </div>
          <p className="mt-1 text-body-s text-ink-secondary">{description}</p>
        </div>
      </CardHeader>

      {inputs && Object.keys(inputs).length > 0 && (
        <div className="px-5 pb-3">
          <pre className="max-h-36 overflow-auto rounded-md border border-edge-subtle bg-canvas-elevated px-3 py-2 font-mono text-mono-s text-ink-secondary">
            {JSON.stringify(inputs, null, 2)}
          </pre>
        </div>
      )}

      <CardBody className="grid grid-cols-2 gap-2 pt-0">
        {ORDER.map((lt) => {
          const meta = LIFETIME_LABELS[lt];
          const isBusy = busy === lt;
          return (
            <Button
              key={lt}
              variant={lt === 'session' ? 'primary' : 'secondary'}
              size="sm"
              disabled={busy != null}
              onClick={() => onAllow(lt)}
              aria-label={meta.label}
              className="flex-col items-start h-auto py-2"
            >
              <span>{isBusy ? 'Granting…' : meta.label}</span>
              <span className="text-[10px] font-normal opacity-70">{meta.hint}</span>
            </Button>
          );
        })}
      </CardBody>

      <CardFooter className="pt-0">
        <Button
          variant="danger"
          size="sm"
          className="w-full"
          disabled={busy != null}
          onClick={onDeny}
          aria-label="Deny"
        >
          {busy === 'deny' ? 'Denying…' : 'Deny'}
        </Button>
      </CardFooter>
    </Card>
  );
}
