// One WebSocket per screen. Reconnects with backoff and asks the screen to re-fetch on reconnect
// (AGENTS.md §8.2). Messages: clock, connection_update, draft_update, options_update,
// notification, reload, ping.
import { useEffect, useRef, useState } from "react";
import type { ReplayState } from "./client";

export type LiveMessage = { type: string; t: string | null; payload: any };

export function useLive(query: string, onMessage: (message: LiveMessage) => void) {
  const handler = useRef(onMessage);
  handler.current = onMessage;
  const [connected, setConnected] = useState(false);
  const [clock, setClock] = useState<ReplayState | null>(null);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let delay = 500;
    let stopped = false;
    let timer: number | undefined;

    const open = () => {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${location.host}/ws?${query}`);
      socket.onopen = () => {
        setConnected(true);
        delay = 500;
        handler.current({ type: "reload", t: null, payload: {} });
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as LiveMessage;
        if (message.type === "ping") return;
        if (message.type === "clock" && message.payload?.scenario_id) setClock(message.payload);
        handler.current(message);
      };
      socket.onclose = () => {
        setConnected(false);
        if (stopped) return;
        timer = window.setTimeout(open, delay);
        delay = Math.min(delay * 2, 8000);
      };
    };
    open();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [query]);

  return { connected, clock };
}
