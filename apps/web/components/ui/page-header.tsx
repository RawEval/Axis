import type { ReactNode } from 'react';

export interface PageHeaderProps {
  title: ReactNode;
  actions?: ReactNode;
}

/**
 * Minimal page header. Just the title and an optional action slot.
 *
 * No eyebrow, no description paragraph — page content carries the context.
 * Description strings were adding noise without improving orientation.
 */
export function PageHeader({ title, actions }: PageHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-4 pb-1">
      <h1 className="truncate text-xl font-semibold tracking-tight text-ink">
        {title}
      </h1>
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}

export interface SectionHeaderProps {
  title: ReactNode;
  actions?: ReactNode;
}

export function SectionHeader({ title, actions }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
