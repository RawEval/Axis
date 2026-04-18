'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, api } from '../api';

export type Tool = 'slack' | 'notion' | 'gmail' | 'gdrive' | 'github';

export type ConnectorTile = {
  tool: Tool;
  project_id?: string;
  status: 'connected' | 'disconnected' | 'pending' | 'revoked' | 'error';
  health: 'green' | 'yellow' | 'red' | null;
  last_sync: string | null;
  permissions: { read: boolean; write: boolean };
  workspace_name?: string | null;
};

export type ConnectStartResponse = {
  tool: Tool;
  status?: string;
  state?: string;
  consent_url?: string;
  using_byo_app?: boolean;
  credential_source?: 'project' | 'org' | 'user' | 'default';
};

/** Tools where a real OAuth flow is wired up on the backend today. */
export const IMPLEMENTED_TOOLS: readonly Tool[] = ['notion', 'slack', 'gmail', 'gdrive', 'github'];

/**
 * The message shape we post from the OAuth popup back to the parent
 * window. The parent listens for this in useOAuthPopupListener().
 */
export type OAuthPopupMessage = {
  type: 'axis:oauth:done';
  tool: string;
  status: 'connected' | 'error';
  message?: string;
};

export function useConnectors() {
  return useQuery<ConnectorTile[]>({
    queryKey: ['connectors'],
    queryFn: () => api.get<ConnectorTile[]>('/connectors'),
    staleTime: 30_000,
  });
}

/**
 * Opens the OAuth consent in a centered popup (600×700). The provider
 * renders the consent screen inside it; after the user approves, the
 * callback redirects to /connections?status=connected&tool=... which
 * detects it's inside a popup (via window.opener), posts a message to
 * the parent, and closes itself. The parent receives the message via
 * useOAuthPopupListener and refreshes the connector list.
 *
 * Edge cases handled:
 *   - Popup blocked by the browser → falls back to top-window navigation
 *   - User closes popup before completing → no-op (parent stays on page)
 *   - Multiple rapid clicks → only one popup opens (deduped by window name)
 *   - Provider refuses to render in popup → the consent page still works;
 *     some providers (Google) open their own window anyway
 *   - Cross-origin postMessage → we verify event.origin matches our app URL
 */
export function useConnectTool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (tool: Tool): Promise<ConnectStartResponse> => {
      const res = await api.post<ConnectStartResponse>(
        `/connectors/${tool}/connect`,
        {},
      );
      if (!res.consent_url) {
        throw new ApiError(
          501,
          res.status === 'not_implemented_yet'
            ? `${tool} isn't wired up yet — coming soon.`
            : 'Cannot start OAuth flow for this tool.',
        );
      }
      return res;
    },
    onSuccess: (res) => {
      if (typeof window === 'undefined' || !res.consent_url) return;

      // Center the popup on the user's screen
      const w = 600;
      const h = 700;
      const left = Math.max(0, Math.round(window.screenX + (window.outerWidth - w) / 2));
      const top = Math.max(0, Math.round(window.screenY + (window.outerHeight - h) / 2));
      const features = `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`;

      // Use a consistent window name per tool so clicking Connect twice
      // focuses the existing popup instead of opening a second one.
      const popup = window.open(res.consent_url, `axis-oauth-${res.tool}`, features);

      if (!popup || popup.closed) {
        // Popup was blocked — fall back to full-page navigation.
        // This is the same behavior as before the popup change, so the
        // user still gets through; they just lose the /connections page
        // state temporarily.
        window.location.href = res.consent_url;
        return;
      }

      // Focus the popup in case it opened behind the current window
      popup.focus();

      // Poll for popup close — if the user closes it manually before
      // the OAuth callback fires, we don't want to leave a dangling
      // listener. This also covers providers that redirect to a
      // different origin (which blocks postMessage).
      const pollTimer = setInterval(() => {
        if (popup.closed) {
          clearInterval(pollTimer);
          // Refresh connectors in case the OAuth completed before the
          // popup's onload could postMessage (race between redirect and
          // close). A redundant query is cheaper than a missed update.
          qc.invalidateQueries({ queryKey: ['connectors'] });
        }
      }, 1000);
    },
  });
}

export function useDisconnectTool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tool: Tool) => api.delete<{ status: string }>(`/connectors/${tool}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['connectors'] }),
  });
}
