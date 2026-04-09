const SSE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api") + "/events/stream";

export type SSEEvent = {
  channel: string;
  data: Record<string, unknown>;
};

export type SSECallback = (event: SSEEvent) => void;

let source: EventSource | null = null;
const listeners = new Set<SSECallback>();

const CHANNELS = [
  "mod_added",
  "mod_removed",
  "mod_updated",
  "vote_created",
  "vote_cast",
  "vote_resolved",
  "upload_pending",
  "upload_resolved",
  "server_status",
  "server_update",
];

export function connectSSE(): void {
  if (source) return;

  source = new EventSource(SSE_URL);

  for (const ch of CHANNELS) {
    source.addEventListener(ch, (e) => {
      const event: SSEEvent = {
        channel: ch,
        data: JSON.parse((e as MessageEvent).data),
      };
      listeners.forEach((cb) => cb(event));
    });
  }

  source.onerror = () => {
    source?.close();
    source = null;
    // Reconnect after 5s
    setTimeout(connectSSE, 5000);
  };
}

export function disconnectSSE(): void {
  source?.close();
  source = null;
}

export function onSSE(cb: SSECallback): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}
