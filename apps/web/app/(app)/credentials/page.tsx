'use client';

import { useState } from 'react';
import {
  Badge,
  Button,
  Field,
  Input,
  PageHeader,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui';
import { ApiError } from '@/lib/api';
import {
  useDeleteOAuthApp,
  useOAuthApps,
  useSaveOAuthApp,
} from '@/lib/queries/oauth-apps';

const TOOLS = [
  {
    tool: 'notion',
    label: 'Notion',
    helpUrl: 'https://www.notion.so/my-integrations',
    docs: 'Create an integration and copy the OAuth client ID + secret.',
  },
  {
    tool: 'slack',
    label: 'Slack',
    helpUrl: 'https://api.slack.com/apps',
    docs: 'Create an app → Basic Information → App Credentials.',
  },
  {
    tool: 'gmail',
    label: 'Gmail',
    helpUrl: 'https://console.cloud.google.com/apis/credentials',
    docs: 'Create an OAuth client ID of type Web application.',
  },
  {
    tool: 'gdrive',
    label: 'Google Drive',
    helpUrl: 'https://console.cloud.google.com/apis/credentials',
    docs: 'Shares the Google OAuth client with Gmail.',
  },
  {
    tool: 'github',
    label: 'GitHub',
    helpUrl: 'https://github.com/settings/apps',
    docs: 'OAuth App or GitHub App — we accept either.',
  },
] as const;

export default function CredentialsPage() {
  const { data: apps } = useOAuthApps();
  const customByTool = new Map((apps ?? []).map((a) => [a.tool, a]));

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-5 px-6 py-6">
      <PageHeader title="Credentials" />

      <div className="space-y-3">
        {TOOLS.map((t) => (
          <CredentialsPanel key={t.tool} tool={t} isCustom={customByTool.has(t.tool)} />
        ))}
      </div>
    </div>
  );
}

function CredentialsPanel({
  tool,
  isCustom,
}: {
  tool: (typeof TOOLS)[number];
  isCustom: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const save = useSaveOAuthApp();
  const del = useDeleteOAuthApp();

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await save.mutateAsync({
        tool: tool.tool,
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
        redirect_uri: redirectUri.trim() || undefined,
      });
      setMessage('Saved. Next connect will use your app.');
      setClientId('');
      setClientSecret('');
      setRedirectUri('');
      setExpanded(false);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'save failed'
          : 'save failed',
      );
    }
  };

  const onDelete = async () => {
    if (!confirm(`Remove your custom ${tool.label} OAuth app?`)) return;
    try {
      await del.mutateAsync(tool.tool);
      setMessage('Custom app removed. Axis default will be used.');
    } catch {
      setError('delete failed');
    }
  };

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-ink">{tool.label}</span>
          {isCustom ? <Badge tone="brand">Custom app</Badge> : <Badge tone="neutral">Axis default</Badge>}
        </div>
        <div className="flex items-center gap-2">
          {isCustom && (
            <Button size="sm" variant="danger" onClick={onDelete}>
              Remove
            </Button>
          )}
          <Button size="sm" variant="secondary" onClick={() => setExpanded((v) => !v)}>
            {expanded ? 'Cancel' : isCustom ? 'Replace' : 'Use your own'}
          </Button>
        </div>
      </PanelHeader>
      <PanelBody>
        <p className="text-sm text-ink-secondary">{tool.docs}</p>
        <a
          href={tool.helpUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-block text-xs text-accent hover:text-accent"
        >
          Open {tool.label} developer console ↗
        </a>

        {expanded && (
          <form onSubmit={onSave} className="mt-4 space-y-3 border-t border-edge pt-4">
            <Field label="Client ID" required>
              <Input value={clientId} onChange={(e) => setClientId(e.target.value)} required />
            </Field>
            <Field label="Client secret" required>
              <Input
                type="password"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                required
              />
            </Field>
            <Field label="Redirect URI" hint="Optional. Defaults to the Axis callback URL.">
              <Input
                type="url"
                value={redirectUri}
                onChange={(e) => setRedirectUri(e.target.value)}
                placeholder="http://localhost:8002/oauth/notion/callback"
              />
            </Field>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setExpanded(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={save.isPending}>
                {save.isPending ? 'Saving…' : 'Save credentials'}
              </Button>
            </div>
          </form>
        )}

        {message && <div className="mt-3 text-xs text-success">{message}</div>}
        {error && <div className="mt-3 text-xs text-danger">{error}</div>}
      </PanelBody>
    </Panel>
  );
}
