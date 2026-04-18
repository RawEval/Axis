import clsx from 'clsx';

export interface SegmentedControlOption<T extends string = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SegmentedControlProps<T extends string = string> {
  value: T;
  onChange: (value: T) => void;
  options: ReadonlyArray<SegmentedControlOption<T>>;
  className?: string;
  'aria-label'?: string;
}

const CONTAINER =
  'inline-flex items-center h-8 p-0.5 rounded-md border border-edge bg-canvas-elevated';

const SEGMENT_BASE =
  'inline-flex items-center justify-center px-3 h-7 rounded-sm font-mono text-[11px] uppercase tracking-[0.06em] transition-colors duration-[120ms] ease-out';

const SEGMENT_ACTIVE = 'bg-canvas-surface text-ink shadow-sm';
const SEGMENT_INACTIVE = 'text-ink-secondary hover:text-ink';

export function SegmentedControl<T extends string = string>({
  value,
  onChange,
  options,
  className,
  ...rest
}: SegmentedControlProps<T>) {
  return (
    <div role="group" className={clsx(CONTAINER, className)} {...rest}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            disabled={opt.disabled}
            aria-pressed={active}
            className={clsx(
              SEGMENT_BASE,
              active ? SEGMENT_ACTIVE : SEGMENT_INACTIVE,
              opt.disabled && 'opacity-40 cursor-not-allowed',
            )}
            onClick={() => {
              if (!active && !opt.disabled) onChange(opt.value);
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
