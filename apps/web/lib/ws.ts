import { getToken } from './auth';

export function connectAxisSocket(onMessage: (msg: unknown) => void): WebSocket {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws';
  const token = getToken();
  const url = token ? `${base}?token=${encodeURIComponent(token)}` : base;
  const ws = new WebSocket(url);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {
      onMessage(ev.data);
    }
  };
  return ws;
}
