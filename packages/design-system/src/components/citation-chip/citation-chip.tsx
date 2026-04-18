import { forwardRef, type HTMLAttributes, type MouseEvent } from 'react';
import clsx from 'clsx';

export interface CitationChipProps extends Omit<HTMLAttributes<HTMLElement>, 'onClick'> {
  index: number;
  sourceId: string;
  sourceTitle?: string;
  onClick?: (sourceId: string) => void;
}

const CHIP =
  'mx-0.5 inline-flex items-center justify-center min-w-[18px] h-4 px-1 rounded-sm bg-accent-subtle text-accent border border-accent/30 font-mono text-[10px] tabular-nums hover:bg-accent hover:text-accent-on transition-colors cursor-pointer';

export const CitationChip = forwardRef<HTMLElement, CitationChipProps>(
  function CitationChip(
    { index, sourceId, sourceTitle, onClick, className, ...rest },
    ref,
  ) {
    const label = sourceTitle ? `Source ${index}: ${sourceTitle}` : `Source ${index}`;
    return (
      <sup ref={ref} className={clsx('citation-chip', className)} {...rest}>
        <button
          type="button"
          aria-label={label}
          onClick={(e: MouseEvent<HTMLButtonElement>) => {
            e.preventDefault();
            onClick?.(sourceId);
          }}
          className={CHIP}
        >
          [{index}]
        </button>
      </sup>
    );
  },
);
