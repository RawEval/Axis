'use client';

import { useSyncExternalStore } from 'react';

export type CapabilityId =
  | 'connector.slack.search'
  | 'connector.slack.channel_summary'
  | 'connector.slack.thread_context'
  | 'connector.slack.user_profile'
  | 'connector.slack.post'
  | 'connector.slack.react'
  | 'connector.notion.search'
  | 'connector.notion.append'
  | 'connector.gmail.search'
  | 'connector.gmail.send'
  | 'connector.gmail.draft'
  | 'connector.gdrive.search'
  | 'connector.gdrive.read_content'
  | 'connector.gdrive.create_doc'
  | 'connector.github.search'
  | 'connector.github.comment'
  | 'connector.github.create_issue';

export type TrustMode = 'ask' | 'auto-reversible' | 'auto';

export interface CapabilityMeta {
  id: CapabilityId;
  label: string;
  tier: 0 | 1 | 2;
  description: string;
}

export const CAPABILITIES: ReadonlyArray<CapabilityMeta> = [
  { id: 'connector.slack.search',          tier: 0, label: 'Search Slack',           description: 'Search messages across channels.' },
  { id: 'connector.slack.channel_summary', tier: 0, label: 'Summarise Slack channel', description: 'Recent activity in a channel.' },
  { id: 'connector.slack.thread_context',  tier: 0, label: 'Read Slack thread',      description: 'Pull replies in a thread for context.' },
  { id: 'connector.slack.user_profile',    tier: 0, label: 'Read Slack profile',     description: 'Look up a Slack user.' },
  { id: 'connector.slack.post',            tier: 1, label: 'Post to Slack',          description: 'Send messages to channels and DMs.' },
  { id: 'connector.slack.react',           tier: 1, label: 'React on Slack',         description: 'Add an emoji reaction to a message.' },
  { id: 'connector.notion.search',         tier: 0, label: 'Search Notion',          description: 'Pages and databases.' },
  { id: 'connector.notion.append',         tier: 1, label: 'Append to Notion',       description: 'Add blocks to an existing page.' },
  { id: 'connector.gmail.search',          tier: 0, label: 'Search Gmail',           description: 'Inbox, labels, threads.' },
  { id: 'connector.gmail.draft',           tier: 1, label: 'Draft Gmail',            description: 'Create a draft — never sends.' },
  { id: 'connector.gmail.send',            tier: 2, label: 'Send Gmail',             description: 'Send email on your behalf — irreversible.' },
  { id: 'connector.gdrive.search',         tier: 0, label: 'Search Google Drive',    description: 'Files and folders.' },
  { id: 'connector.gdrive.read_content',   tier: 0, label: 'Read Drive content',     description: 'Open Docs, Sheets, Slides text.' },
  { id: 'connector.gdrive.create_doc',     tier: 1, label: 'Create Google Doc',      description: 'Create a new doc in Drive.' },
  { id: 'connector.github.search',         tier: 0, label: 'Search GitHub',          description: 'Issues, PRs, code.' },
  { id: 'connector.github.comment',        tier: 1, label: 'Comment on GitHub',      description: 'Comment on issues and PRs.' },
  { id: 'connector.github.create_issue',   tier: 1, label: 'Create GitHub issue',    description: 'File a new issue in a repo.' },
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
