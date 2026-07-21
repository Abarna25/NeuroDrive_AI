import { useEffect, useRef, useState } from 'react';
import { StreamData, WS_URL } from '../types';

const RECONNECT_DELAY_MS = 3000;
const MAX_RETRIES = 5;

export function useWebSocket() {
  const [data, setData] = useState<StreamData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const retriesRef = useRef(0);

  useEffect(() => {
    // `disposed` is scoped to this effect run so a socket created by a
    // previous mount (React StrictMode remounts) can never schedule a
    // reconnect after cleanup — that would leave two live sockets and
    // deliver every message twice.
    let disposed = false;
    let reconnectTimer: number | undefined;
    let ws: WebSocket | null = null;

    const connect = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        retriesRef.current = 0;
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const parsed: StreamData = JSON.parse(event.data);
          if (parsed.error) {
            setError(parsed.error);
            return;
          }
          if (parsed.status_message) {
            return; // backend still loading models
          }
          setData(parsed);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (disposed) return;
        if (retriesRef.current < MAX_RETRIES) {
          retriesRef.current += 1;
          reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
        } else {
          setError('Connection lost — is the backend running on port 8000?');
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { data, isConnected, error };
}
