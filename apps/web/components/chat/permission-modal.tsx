'use client';

import { useState } from 'react';
import { Button } from '@/components/ui';
import {
  useResolvePermission,
  type PermissionLifetime,
} from '@/lib/queries/live';

export type PermissionRequest = {
  pending_id: string;
  capability: string;
  description: string;
  inputs: Record<string, unknown>;
};

const LIFETIME_OPTIONS: Array<{ value: PermissionLifetime; label: string; hint: string }> = [
  { value: 'session', label: 'Allow once', hint: 'just this call' },
  { value: 'project', label: 'Allow for project', hint: 'remember for this workspace' },
  { value: '24h', label: 'Allow 24h', hint: 're-ask tomorrow' },
  { value: 'forever', label: 'Allow forever', hint: 'across all sessions' },
];

export function PermissionModal({
  request,
  onResolved,
}: {
  request: PermissionRequest;
  onResolved: () => void;
}) {
  const resolve = useResolvePermission();
  const [pending, setPending] = useState<PermissionLifetime | 'deny' | null>(null);

  const act = async (decision: PermissionLifetime | 'deny') => {
    if (resolve.isPending) return;
    setPending(decision);
    try {
      await resolve.mutateAsync({
        pending_id: request.pending_id,
        granted: decision !== 'deny',
        lifetime: decision === 'deny' ? 'session' : decision,
      });
      onResolved();
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-lg border border-canvas-subtle bg-canvas-surface p-5 shadow-xl">
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-warning" />
          <h2 className="text-sm font-semibold text-ink">
            Axis wants to use <span className="font-mono">{request.capability}</span>
          </h2>
        </div>
        <p className="mb-3 text-xs text-ink-secondary">{request.description}</p>
        {Object.keys(request.inputs).length > 0 && (
          <pre className="mb-4 max-h-32 overflow-auto rounded border border-canvas-subtle bg-canvas px-2 py-1.5 text-[11px] text-ink-secondary">
            {JSON.stringify(request.inputs, null, 2)}
          </pre>
        )}
        <div className="grid grid-cols-2 gap-2">
          {LIFETIME_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={opt.value === 'session' ? 'primary' : 'secondary'}
              size="sm"
              disabled={resolve.isPending}
              onClick={() => act(opt.value)}
            >
              <div className="flex flex-col items-start">
                <span>
                  {pending === opt.value ? 'Granting…' : opt.label}
                </span>
                <span className="text-[10px] font-normal opacity-70">{opt.hint}</span>
              </div>
            </Button>
          ))}
        </div>
        <div className="mt-2">
          <Button
            variant="danger"
            size="sm"
            className="w-full"
            disabled={resolve.isPending}
            onClick={() => act('deny')}
          >
            {pending === 'deny' ? 'Denying…' : 'Deny'}
          </Button>
        </div>
      </div>
    </div>
  );
}
