'use client';

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  type KeyboardEvent,
  type TextareaHTMLAttributes,
} from 'react';
import clsx from 'clsx';

export interface PromptInputProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange' | 'onSubmit'> {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  busy?: boolean;
  /** min height in px (default 80). */
  minHeight?: number;
  /** max height in px before scroll (default 240). */
  maxHeight?: number;
}

const WRAPPER =
  'relative flex items-end gap-2 rounded-md border border-edge bg-canvas-surface px-3 py-2 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20 transition-colors';

const TEXTAREA_BASE =
  'flex-1 resize-none bg-transparent text-body text-ink placeholder:text-ink-tertiary focus:outline-none disabled:opacity-50';

const SEND_BASE =
  'inline-flex items-center justify-center h-8 px-4 rounded-sm font-mono text-[11px] uppercase tracking-[0.06em] transition-colors disabled:opacity-40 disabled:cursor-not-allowed';

const SEND_ACTIVE = 'bg-accent text-accent-on hover:bg-accent-hover';
const SEND_INACTIVE = 'bg-canvas-elevated text-ink-tertiary';

export const PromptInput = forwardRef<HTMLTextAreaElement, PromptInputProps>(
  function PromptInput(
    {
      value,
      onChange,
      onSubmit,
      busy = false,
      minHeight = 80,
      maxHeight = 240,
      placeholder = 'Type a message, or /command',
      className,
      style,
      ...rest
    },
    ref,
  ) {
    const innerRef = useRef<HTMLTextAreaElement | null>(null);
    useImperativeHandle(ref, () => innerRef.current as HTMLTextAreaElement);

    const resize = useCallback(() => {
      const el = innerRef.current;
      if (!el) return;
      el.style.height = 'auto';
      const next = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
      el.style.height = `${next}px`;
      el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
    }, [minHeight, maxHeight]);

    useEffect(() => {
      resize();
    }, [value, resize]);

    const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!busy && value.trim().length > 0) onSubmit(value);
        return;
      }
    };

    const canSend = !busy && value.trim().length > 0;

    return (
      <div className={clsx(WRAPPER, className)} style={style}>
        <textarea
          ref={innerRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={busy}
          rows={3}
          className={TEXTAREA_BASE}
          style={{ minHeight }}
          {...rest}
        />
        <button
          type="button"
          aria-label="Send"
          disabled={!canSend}
          onClick={() => onSubmit(value)}
          className={clsx(SEND_BASE, canSend ? SEND_ACTIVE : SEND_INACTIVE)}
        >
          Send
        </button>
      </div>
    );
  },
);
