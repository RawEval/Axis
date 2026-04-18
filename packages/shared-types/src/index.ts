// Mirrors the data model in docs/axis_full_spec.docx §09.
// Keep in sync with Pydantic models in services/*/app/schemas.

export type Plan = 'free' | 'pro' | 'team' | 'enterprise';
export type TrustLevel = 'low' | 'medium' | 'high';
export type ConnectorTool =
  | 'slack'
  | 'notion'
  | 'gmail'
  | 'gdrive'
  | 'github'
  | 'linear'
  | 'gcalendar'
  | 'jira'
  | 'airtable'
  | 'local_fs'
  | 'confluence'
  | 'hubspot'
  | 'figma'
  | 'zoom'
  | 'obsidian';

export type HealthStatus = 'green' | 'yellow' | 'red';

export interface User {
  id: string;
  email: string;
  name: string | null;
  plan: Plan;
  settings: {
    brief_time?: string;
    max_proactive_per_day?: number;
    trust_level?: TrustLevel;
    output_format?: 'concise' | 'detailed';
  };
  usage: {
    actions_this_month?: number;
    tokens_consumed?: number;
  };
  created_at: string;
}

export interface Connector {
  id: string;
  user_id: string;
  tool_name: ConnectorTool;
  status: 'pending' | 'connected' | 'revoked' | 'error';
  permissions: { read: boolean; write: boolean };
  last_sync: string | null;
  health_status: HealthStatus;
}

export interface PlanStep {
  step: number;
  tool: ConnectorTool;
  action: string;
  status: 'pending' | 'running' | 'done' | 'error';
}

export interface AgentAction {
  id: string;
  user_id: string;
  prompt: string;
  plan: PlanStep[];
  result: {
    output: string;
    sources: Array<{ tool: ConnectorTool; ref: string }>;
    tokens_used: number;
    latency_ms: number;
  } | null;
  eval_score: {
    faithfulness: number;
    correctness: number;
    relevance: number;
  } | null;
  timestamp: string;
}

export interface WriteAction {
  id: string;
  action_id: string;
  tool: ConnectorTool;
  target_id: string;
  target_type: string;
  diff: { before: string; after: string };
  confirmed_by_user: boolean;
  rolled_back: boolean;
}

export interface ProactiveSurface {
  id: string;
  user_id: string;
  signal_type:
    | 'unanswered_message'
    | 'stale_doc'
    | 'contradiction'
    | 'unrecorded_decision'
    | 'approaching_deadline'
    | 'followup_candidate';
  title: string;
  context_snippet: string;
  confidence_score: number;
  proposed_action: { label: string; action_id: string } | null;
  status: 'pending' | 'accepted' | 'dismissed';
  created_at: string;
}

export type MemoryTier = 'episodic' | 'semantic' | 'procedural';

export interface MemoryNode {
  id: string;
  user_id: string;
  type: MemoryTier;
  content: string;
  created_at: string;
  last_accessed: string;
  decay_score: number;
  pinned: boolean;
}
