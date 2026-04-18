'use client';

import { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../api';
import { connectAxisSocket } from '../ws';

export type LiveEvent = {
  type: string;
  user_id?: string;
  project_id?: string | null;
  action_id?: string | null;
  task_id?: string | null;
  step_id?: string | null;
  payload?: Record<string, unknown>;
  ts?: string;
};

/**
 * Open a singleton WebSocket to the gateway and accumulate every event
 * in component state. The hook auto-reconnects once on error and
 * disposes cleanly on unmount.
 */
export function useLiveEvents() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | null = null;

    const open = () => {
      if (cancelled) return;
      ws = connectAxisSocket((msg) => {
        if (cancelled) return;
        const ev = msg as LiveEvent;
        if (ev && typeof ev === 'object' && 'type' in ev) {
          setEvents((prev) => [...prev, ev]);
        }
      });
      ws.onopen = () => {
        if (!cancelled) setConnected(true);
      };
      ws.onclose = () => {
        if (!cancelled) setConnected(false);
      };
      ws.onerror = () => {
        if (!cancelled) setConnected(false);
      };
    };

    open();
    return () => {
      cancelled = true;
      try {
        ws?.close();
      } catch {
        /* ignore */
      }
    };
  }, []);

  const clear = () => setEvents([]);

  return { events, connected, clear };
}

export type PermissionLifetime = 'session' | '24h' | 'project' | 'forever';

export function useResolvePermission() {
  return useMutation({
    mutationFn: (input: {
      pending_id: string;
      granted: boolean;
      lifetime: PermissionLifetime;
    }) =>
      api.post<{ ok: boolean; pending_id: string }>(
        '/permissions/resolve',
        input,
      ),
  });
}
