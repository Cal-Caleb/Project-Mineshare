import { useEffect } from "react";
import { connectSSE, onSSE, type SSECallback } from "../lib/sse";

/**
 * Subscribe to SSE events. Optionally filter by channel name(s).
 *
 * Usage:
 *   useSSE((e) => console.log(e));                       // all events
 *   useSSE((e) => refetch(), ["vote_cast", "vote_resolved"]); // specific channels
 */
export function useSSE(callback: SSECallback, channels?: string[]): void {
  useEffect(() => {
    connectSSE();

    const wrapped: SSECallback = (event) => {
      if (!channels || channels.includes(event.channel)) {
        callback(event);
      }
    };

    return onSSE(wrapped);
  }, [callback, channels]);
}
