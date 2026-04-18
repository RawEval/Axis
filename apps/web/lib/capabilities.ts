'use client';

import { useSyncExternalStore } from 'react';

export type CapabilityId =
  | 'connector.slack.read'
  | 'connector.slack.write'
  | 'connector.notion.read'
  | 'connector.notion.write'
  | 'connector.gmail.read'
  | 'connector.gmail.send'
  | 'connector.gdrive.read'
  | 'connector.github.read'
  | 'connector.github.write';

export type TrustMode = 'ask' | 'auto-reversible' | 'auto';

export interface CapabilityMeta {
  id: CapabilityId;
  label: string;
  tier: 0 | 1 | 2;
  description: string;
}

export const CAPABILITIES: ReadonlyArray<CapabilityMeta> = [
  { id: 'connector.slack.read',    tier: 0, label: 'Read Slack',          description: 'Channels, threads, search.' },
  { id: 'connector.slack.write',   tier: 1, label: 'Post to Slack',       description: 'Send messages to channels and DMs.' },
  { id: 'connector.notion.read',   tier: 0, label: 'Read Notion',         description: 'Pages, databases, search.' },
  { id: 'connector.notion.write',  tier: 1, label: 'Edit Notion',         description: 'Create + update pages.' },
  { id: 'connector.gmail.read',    tier: 0, label: 'Read Gmail',          description: 'Inbox, labels, search.' },
  { id: 'connector.gmail.send',    tier: 2, label: 'Send Gmail',          description: 'Send email on your behalf — irreversible.' },
  { id: 'connector.gdrive.read',   tier: 0, label: 'Read Google Drive',   description: 'Files, folders, content.' },
  { id: 'connector.github.read',   tier: 0, label: 'Read GitHub',         description: 'Issues, PRs, code.' },
  { id: 'connector.github.write',  tier: 1, label: 'Comment on GitHub',   description: 'Comment on issues + PRs.' },
];

const STORAGE_KEY = 'axis.capabilities';

type State = Record<CapabilityId, TrustMode>;

function defaultMode(meta: CapabilityMeta): TrustMode {
  return meta.tier === 0 ? 'auto' : meta.tier === 1 ? 'ask' : 'ask';
}

function readStored(): State {
  if (typeof window === 'undefined') {
    return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
    }
    const parsed = JSON.parse(raw) as Partial<State>;
    return Object.fromEntries(
      CAPABILITIES.map((c) => [c.id, parsed[c.id] ?? defaultMode(c)]),
    ) as State;
  } catch {
    return Object.fromEntries(CAPABILITIES.map((c) => [c.id, defaultMode(c)])) as State;
  }
}

let state: State = readStored();
const listeners = new Set<() => void>();

function emit(): void {
  for (const l of listeners) l();
}

export const capabilities = {
  getState: (): State => state,
  setMode: (id: CapabilityId, mode: TrustMode): void => {
    state = { ...state, [id]: mode };
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
    emit();
  },
  subscribe: (l: () => void) => {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
};

export function useCapabilities(): State {
  return useSyncExternalStore(capabilities.subscribe, capabilities.getState, capabilities.getState);
}
