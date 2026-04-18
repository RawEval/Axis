'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, Button, PageHeader } from '@/components/ui';
import { ApiError } from '@/lib/api';
import {
  IMPLEMENTED_TOOLS,
  type ConnectorTile,
  type OAuthPopupMessage,
  type Tool,
  useConnectTool,
  useConnectors,
  useDisconnectTool,
} from '@/lib/queries/connectors';

type Banner = { tone: 'success' | 'danger'; message: string } | null;

interface ToolMeta {
  tool: Tool;
  label: string;
  icon: string;
  color: string;
  desc: string;
}

export default function ConnectionsContent({ tools }: { tools: ToolMeta[] }) {
  const qc = useQueryClient();
  const { data, isLoading } = useConnectors();
  const connect = useConnectTool();
  const disconnect = useDisconnectTool();
  const params = useSearchParams();
  const [banner, setBanner] = useState<Banner>(null);
  const isPopup = useRef(false);

  // Popup child: detect we're inside the OAuth popup, post message, close
  useEffect(() => {
    if (typeof window === 'undefined' || !window.opener) return;
    isPopup.current = true;
    const status = params.get('status');
    const tool = params.get('tool');
    if (status && tool) {
      const msg: OAuthPopupMessage = {
        type: 'axis:oauth:done',
        tool,
        status: status === 'connected' ? 'connected' : 'error',
        message: params.get('message') ?? undefined,
      };
      try { window.opener.postMessage(msg, window.location.origin); } catch {}
    }
    const timer = setTimeout(() => window.close(), 300);
    return () => clearTimeout(timer);
  }, [params]);

  // Parent: listen for popup postMessage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handler = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const msg = event.data as OAuthPopupMessage | null;
      if (!msg || msg.type !== 'axis:oauth:done') return;
      const label = tools.find((t) => t.tool === msg.tool)?.label ?? msg.tool;
      setBanner({
        tone: msg.status === 'connected' ? 'success' : 'danger',
        message: msg.status === 'connected' ? `${label} connected.` : `${label}: ${msg.message ?? 'failed'}`,
      });
      qc.invalidateQueries({ queryKey: ['connectors'] });
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [qc, tools]);

  // Fallback: direct navigation (popup blocked)
  useEffect(() => {
    if (isPopup.current) return;
    const status = params.get('status');
    const tool = params.get('tool');
    if (!status || !tool) return;
    const label = tools.find((t) => t.tool === tool)?.label ?? tool;
    setBanner({
      tone: status === 'connected' ? 'success' : 'danger',
      message: status === 'connected' ? `${label} connected.` : `${label}: ${params.get('message') ?? 'failed'}`,
    });
    if (window.history.replaceState) window.history.replaceState({}, '', '/connections');
  }, [params, tools]);

  const onConnect = useCallback(
    async (tool: ConnectorTile['tool']) => {
      setBanner(null);
      try { await connect.mutateAsync(tool); } catch (err) {
        setBanner({ tone: 'danger', message: err instanceof ApiError ? String(err.detail ?? err.message) : 'Failed to connect.' });
      }
    },
    [connect],
  );

  if (isPopup.current) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="text-center">
          <div className="mb-2 text-base font-semibold text-ink">Connecting...</div>
          <div className="text-sm text-ink-tertiary">This window will close automatically.</div>
        </div>
      </div>
    );
  }

  const connectedMap = new Map<string, ConnectorTile>((data ?? []).map((t) => [t.tool, t]));

  return (
    <div className="mx-auto flex min-h-full max-w-5xl flex-col gap-6 px-6 py-6">
      <PageHeader title="Connected tools" />

      {banner && (
        <div className={
          banner.tone === 'success'
            ? 'rounded-lg border border-success/20 bg-success/10 px-4 py-3 text-sm text-success'
            : 'rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger'
        }>
          {banner.message}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-xl border border-edge bg-canvas-surface" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map((t) => {
            const tile = connectedMap.get(t.tool);
            const connected = tile?.status === 'connected';
            const implemented = IMPLEMENTED_TOOLS.includes(t.tool);
            return (
              <ToolCard
                key={t.tool}
                tool={t}
                tile={tile}
                connected={connected}
                implemented={implemented}
                onConnect={() => onConnect(t.tool)}
                onDisconnect={() => disconnect.mutate(t.tool)}
                pending={connect.isPending}
              />
            );
          })}
        </div>
      )}

      <p className="text-xs text-ink-tertiary">
        Using your own OAuth app?{' '}
        <a href="/credentials" className="text-accent hover:underline">Configure credentials</a>
      </p>
    </div>
  );
}

function ToolCard({
  tool,
  tile,
  connected,
  implemented,
  onConnect,
  onDisconnect,
  pending,
}: {
  tool: ToolMeta;
  tile: ConnectorTile | undefined;
  connected: boolean;
  implemented: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  pending: boolean;
}) {
  return (
    <div className="group relative flex flex-col rounded-xl border border-edge bg-canvas-surface p-5 shadow-e1 transition-shadow hover:shadow-e2">
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg font-bold text-white ${tool.color}`}>
            {tool.icon}
          </div>
          <div>
            <div className="text-sm font-semibold text-ink">{tool.label}</div>
            <div className="text-xs text-ink-tertiary">{tool.desc}</div>
          </div>
        </div>
        {connected && (
          <span className="mt-1 flex h-2.5 w-2.5 rounded-full bg-success" title="Connected" />
        )}
      </div>

      {connected && tile && (
        <div className="mb-3 rounded-md bg-canvas-elevated px-3 py-2 text-xs text-ink-secondary">
          <div className="flex items-center justify-between">
            <span className="font-medium">{tile.workspace_name || 'Connected'}</span>
            <Badge tone={tile.health === 'green' ? 'success' : tile.health === 'yellow' ? 'warning' : 'neutral'}>
              {tile.health ?? 'ok'}
            </Badge>
          </div>
          {tile.last_sync && (
            <div className="mt-1 text-ink-tertiary">
              Synced {new Date(tile.last_sync).toLocaleString()}
            </div>
          )}
        </div>
      )}

      <div className="mt-auto pt-2">
        {connected ? (
          <div className="flex items-center justify-between">
            <Badge tone="success">Connected</Badge>
            <button
              onClick={onDisconnect}
              className="text-xs text-ink-tertiary transition-colors hover:text-danger"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <Button
            variant="primary"
            size="sm"
            onClick={onConnect}
            disabled={!implemented || pending}
            className="w-full"
          >
            {!implemented ? 'Coming soon' : pending ? 'Connecting...' : `Connect ${tool.label}`}
          </Button>
        )}
      </div>
    </div>
  );
}
