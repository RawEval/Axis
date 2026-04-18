'use client';

import { type ReactNode } from 'react';
import clsx from 'clsx';
import { Card, CardHeader, CardBody, CardFooter } from '../card';
import { Button } from '../button';

export interface WritePreviewMeta {
  label: string;
  value: ReactNode;
}

export interface WritePreviewCardProps {
  title: string;
  meta?: ReadonlyArray<WritePreviewMeta>;
  children?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
  onEdit?: () => void;
  onRefine?: () => void;
  busy?: boolean;
  className?: string;
}

export function WritePreviewCard({
  title,
  meta,
  children,
  onConfirm,
  onCancel,
  onEdit,
  onRefine,
  busy = false,
  className,
}: WritePreviewCardProps) {
  return (
    <Card className={clsx('shadow-e1', className)}>
      <CardHeader className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Write preview
        </span>
        <span className="text-body-s font-medium text-ink">{title}</span>
      </CardHeader>

      {meta && meta.length > 0 && (
        <div className="px-5 py-3 border-b border-edge-subtle space-y-1">
          {meta.map((m, i) => (
            <div key={i} className="flex items-baseline gap-3 text-body-s">
              <span className="w-12 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                {m.label}
              </span>
              <span className="text-ink">{m.value}</span>
            </div>
          ))}
        </div>
      )}

      <CardBody>{children}</CardBody>

      <CardFooter className="flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        {onEdit && (
          <Button variant="secondary" size="sm" onClick={onEdit} disabled={busy}>
            Edit
          </Button>
        )}
        {onRefine && (
          <Button variant="secondary" size="sm" onClick={onRefine} disabled={busy}>
            Refine
          </Button>
        )}
        <Button variant="primary" size="sm" onClick={onConfirm} disabled={busy}>
          {busy ? 'Sending…' : 'Confirm'}
        </Button>
      </CardFooter>
    </Card>
  );
}
