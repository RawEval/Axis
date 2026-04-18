import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type BreathingTone =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background';

export type BreathingSize = 'sm' | 'md' | 'lg';

export interface BreathingPulseProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  tone?: BreathingTone;
  size?: BreathingSize;
}

const TONE: Record<BreathingTone, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
};

const SIZE: Record<BreathingSize, string> = {
  sm: 'h-1.5 w-1.5',
  md: 'h-2 w-2',
  lg: 'h-3 w-3',
};

export const BreathingPulse = forwardRef<HTMLSpanElement, BreathingPulseProps>(
  function BreathingPulse({ tone = 'running', size = 'md', className, ...rest }, ref) {
    return (
      <span
        ref={ref}
        aria-hidden="true"
        className={clsx('inline-block rounded-full animate-breathe', TONE[tone], SIZE[size], className)}
        {...rest}
      />
    );
  },
);
