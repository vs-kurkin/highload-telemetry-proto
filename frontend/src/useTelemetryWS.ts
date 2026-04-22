import { useEffect, useRef, useCallback } from 'react';
import { useTelemetryStore } from './store';
import { UI_CONFIG } from './config';

interface TelemetryData {
  battery: number;
  status: string;
}

interface AlertPayload {
  id: number;
  robot_id: string;
  message: string;
  battery: number;
}

interface WSAlertMessage {
  type: 'alert';
  payload: AlertPayload;
}

interface WSTelemetryMessage {
  type: 'telemetry_update';
  data: Record<string, TelemetryData>;
}

function isAlertMessage(msg: unknown): msg is WSAlertMessage {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    'type' in msg &&
    (msg as Record<string, unknown>).type === 'alert'
  );
}

function isTelemetryUpdateMessage(msg: unknown): msg is WSTelemetryMessage {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    'type' in msg &&
    (msg as Record<string, unknown>).type === 'telemetry_update'
  );
}

/**
 * Custom hook for managing telemetry WebSocket connection.
 * Handles authentication, automatic reconnection, and message dispatching.
 */
export function useTelemetryWS() {
  const { throttledUpdateTelemetry, addAlert, setWsStatus } = useTelemetryStore();
  const reconnectTimeoutRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const wsUrl = UI_CONFIG.WS_URL;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WS CONNECTED");
      setWsStatus(true);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        if (isAlertMessage(data)) {
          addAlert(data.payload);
        } else if (isTelemetryUpdateMessage(data)) {
          throttledUpdateTelemetry(data.data);
        } else if (typeof data === 'object' && !data.type) {
          // Fallback for raw map
          throttledUpdateTelemetry(data);
        }
      } catch {
        // Silently fail parsing
      }
    };

    ws.onclose = () => {
      setWsStatus(false);
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [addAlert, throttledUpdateTelemetry, setWsStatus]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  return { ws: wsRef.current };
}
