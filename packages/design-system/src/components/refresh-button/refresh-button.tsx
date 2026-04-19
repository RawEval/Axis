'use client';
import * as React from 'react';

export type RefreshButtonProps = {
  /** Async refresh trigger — usually `useFreshen(source).mutateAsync` from apps/web. */
  onRefresh: () => Promise<unknown>;
  source: string;
  isPending?: boolean;
  'data-testid'?: string;
};

export function RefreshButton({
  onRefresh,
  source,
  isPending,
  'data-testid': testId,
}: RefreshButtonProps) {
  const [internalPending, setPending] = React.useState(false);
  const pending = isPending ?? internalPending;

  return (
    <button
      type="button"
      onClick={async () => {
        setPending(true);
        try {
          await onRefresh();
        } finally {
          setPending(false);
        }
      }}
      disabled={pending}
      data-testid={testId}
      aria-label={`Refresh ${source}`}
      className="text-xs underline text-ink-secondary hover:text-ink disabled:opacity-50"
    >
      {pending ? 'Refreshing…' : 'Refresh'}
    </button>
  );
}
