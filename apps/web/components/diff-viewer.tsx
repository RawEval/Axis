'use client';

import clsx from 'clsx';

type DiffLine = { type: 'add' | 'del' | 'eq'; text: string };

export function DiffViewer({ lines }: { lines: DiffLine[] }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-edge bg-canvas-surface p-4 font-mono text-xs leading-relaxed text-ink">
      {lines.map((line, i) => (
        <div
          key={i}
          className={clsx(
            line.type === 'add' && 'bg-success/60 text-success',
            line.type === 'del' && 'bg-danger/60 text-danger line-through',
            line.type === 'eq' && 'text-ink-secondary',
          )}
        >
          <span className="mr-2 select-none">
            {line.type === 'add' ? '+' : line.type === 'del' ? '−' : ' '}
          </span>
          {line.text}
        </div>
      ))}
    </pre>
  );
}
