import { useSyncExternalStore } from 'react';

export type ToastTone = 'info' | 'success' | 'warning' | 'danger' | 'action';

export interface ToastItem {
  id: string;
  tone: ToastTone;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  /** ms; undefined = no auto-dismiss. */
  durationMs?: number;
}

type Store = {
  toasts: ToastItem[];
};

const listeners = new Set<() => void>();
let state: Store = { toasts: [] };

function emit() {
  for (const l of listeners) l();
}

export const useToasts = (() => {
  const subscribe = (l: () => void) => {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  };
  const getSnapshot = () => state;
  const setState = (next: Store | ((prev: Store) => Store)) => {
    state = typeof next === 'function' ? (next as (p: Store) => Store)(state) : next;
    emit();
  };

  function hook(): Store {
    return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  }

  hook.setState = setState;
  hook.getState = () => state;
  return hook;
})();

let counter = 0;
function makeId(): string {
  counter += 1;
  return `toast_${counter}`;
}

export function pushToast(input: Omit<ToastItem, 'id'>): string {
  const id = makeId();
  const item: ToastItem = { id, ...input };
  useToasts.setState((s) => ({ toasts: [...s.toasts, item] }));
  if (item.durationMs && item.durationMs > 0) {
    setTimeout(() => dismissToast(id), item.durationMs);
  }
  return id;
}

export function dismissToast(id: string): void {
  useToasts.setState((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
}
