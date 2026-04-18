import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export type DiffLineType = 'add' | 'del' | 'eq';

export interface DiffLine {
  type: DiffLineType;
  text: string;
}

export interface DiffViewerProps extends HTMLAttributes<HTMLDivElement> {
  lines: ReadonlyArray<DiffLine>;
  /** Optional header (e.g. file path) above the diff. */
  header?: ReactNode;
}

const ROW_BASE =
  'flex items-baseline gap-3 px-3 py-0.5 font-mono text-[13px] leading-relaxed whitespace-pre-wrap';

const ROW_CLASSES: Record<DiffLineType, string> = {
  add: 'bg-success/10 text-success',
  del: 'bg-danger/10 text-danger line-through',
  eq:  'text-ink-secondary',
};

const PREFIX: Record<DiffLineType, string> = {
  add: '+',
  del: '−',
  eq:  ' ',
};

export function DiffViewer({ lines, header, className, ...rest }: DiffViewerProps) {
  return (
    <div
      className={clsx('overflow-hidden rounded-md border border-edge bg-canvas-surface', className)}
      {...rest}
    >
      {header && (
        <div className="px-3 py-2 border-b border-edge-subtle font-mono text-mono-s text-ink-tertiary">
          {header}
        </div>
      )}
      <div className="overflow-x-auto py-1">
        {lines.map((line, i) => (
          <div key={i} className={clsx(ROW_BASE, ROW_CLASSES[line.type])}>
            <span aria-hidden="true" className="select-none w-3 text-center text-ink-tertiary">
              {PREFIX[line.type]}
            </span>
            <span>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
