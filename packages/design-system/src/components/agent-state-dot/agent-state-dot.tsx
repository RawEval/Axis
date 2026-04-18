import { forwardRef, type HTMLAttributes } from 'react';
import clsx from 'clsx';

export type AgentState =
  | 'thinking' | 'running' | 'awaiting' | 'recovered' | 'blocked' | 'background' | 'done';

export interface AgentStateDotProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  state: AgentState;
  /** Override the screen-reader label (defaults to the state title-cased). */
  label?: string;
}

const TONE: Record<AgentState, string> = {
  thinking:   'bg-agent-thinking',
  running:    'bg-agent-running',
  awaiting:   'bg-agent-awaiting',
  recovered:  'bg-agent-recovered',
  blocked:    'bg-agent-blocked',
  background: 'bg-agent-background',
  done:       'bg-success',
};

const PULSING: ReadonlySet<AgentState> = new Set(['thinking', 'running', 'awaiting']);

const DEFAULT_LABEL: Record<AgentState, string> = {
  thinking:   'Thinking',
  running:    'Running',
  awaiting:   'Awaiting permission',
  recovered:  'Recovered',
  blocked:    'Blocked',
  background: 'Backgrounded',
  done:       'Done',
};

export const AgentStateDot = forwardRef<HTMLSpanElement, AgentStateDotProps>(
  function AgentStateDot({ state, label, className, ...rest }, ref) {
    const text = label ?? DEFAULT_LABEL[state];
    return (
      <span ref={ref} className={clsx('inline-flex items-center', className)} {...rest}>
        <span
          aria-hidden="true"
          className={clsx(
            'inline-block h-2 w-2 rounded-full',
            TONE[state],
            PULSING.has(state) && 'animate-breathe',
          )}
        />
        <span className="sr-only">{text}</span>
      </span>
    );
  },
);
