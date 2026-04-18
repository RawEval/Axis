'use client';

import { useState } from 'react';
import {
  PermissionCard,
  type PermissionDecision,
  type PermissionLifetime,
} from '@axis/design-system';
import {
  useResolvePermission,
} from '@/lib/queries/live';

export type PermissionRequest = {
  pending_id: string;
  capability: string;
  description: string;
  inputs: Record<string, unknown>;
};

export function PermissionModal({
  request,
  onResolved,
}: {
  request: PermissionRequest;
  onResolved: () => void;
}) {
  const resolve = useResolvePermission();
  const [busy, setBusy] = useState<PermissionDecision | null>(null);

  const decide = async (decision: PermissionDecision) => {
    if (resolve.isPending) return;
    setBusy(decision);
    try {
      await resolve.mutateAsync({
        pending_id: request.pending_id,
        granted: decision !== 'deny',
        lifetime: decision === 'deny' ? 'session' : decision,
      });
      onResolved();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md">
        <PermissionCard
          capability={request.capability}
          description={request.description}
          inputs={request.inputs}
          busy={busy}
          onAllow={(lt: PermissionLifetime) => decide(lt)}
          onDeny={() => decide('deny')}
        />
      </div>
    </div>
  );
}
