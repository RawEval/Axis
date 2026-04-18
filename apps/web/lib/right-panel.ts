import { useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';

export interface RightPanelContent {
  title: string;
  body: ReactNode;
}

interface RightPanelState extends Partial<RightPanelContent> {
  open: boolean;
}

let state: RightPanelState = { open: false };
const listeners = new Set<() => void>();

function emit(): void {
  for (const l of listeners) l();
}

function setState(next: RightPanelState): void {
  state = next;
  emit();
}

export const rightPanel = {
  getState: (): RightPanelState => state,
  open(content: RightPanelContent): void {
    setState({ open: true, ...content });
  },
  close(): void {
    setState({ open: false });
  },
  subscribe(l: () => void): () => void {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
};

export function useRightPanel(): RightPanelState {
  return useSyncExternalStore(rightPanel.subscribe, rightPanel.getState, rightPanel.getState);
}
