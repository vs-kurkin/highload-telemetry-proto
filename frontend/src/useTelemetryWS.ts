import { useEffect, useRef } from 'react';
import { useTelemetryStore } from '@/store';
import { UI_CONFIG } from '@/config';
// @ts-expect-error - Web Worker import might need special handling in some environments - Vite handles worker import with ?worker
import TelemetryWorker from '@/telemetry.worker?worker';

/**
 * Custom hook for managing telemetry WebSocket connection via Web Worker.
 * Offloads JSON parsing and handles intelligent subscriptions based on visibility.
 */
export function useTelemetryWS() {
  const { 
    updateTelemetryBatch, addAlert, setWsStatus, visibleRobotIds 
  } = useTelemetryStore();
  
  const workerRef = useRef<Worker | null>(null);
  const prevVisibleIds = useRef<string[]>([]);

  useEffect(() => {
    // Initialize Worker
    const worker = new TelemetryWorker();
    workerRef.current = worker;

    worker.postMessage({ type: 'CONNECT', payload: UI_CONFIG.WS_URL });

    worker.onmessage = (e: MessageEvent) => {
      const { type, payload } = e.data;

      switch (type) {
        case 'WS_STATUS':
          setWsStatus(payload);
          break;
        case 'ALERT':
          addAlert(payload);
          break;
        case 'TELEMETRY_BATCH':
          updateTelemetryBatch(payload);
          break;
      }
    };

    return () => {
      worker.terminate();
    };
  }, [addAlert, updateTelemetryBatch, setWsStatus]);

  // Handle Subscriptions based on visibility
  useEffect(() => {
    if (!workerRef.current) return;

    const added = visibleRobotIds.filter(id => !prevVisibleIds.current.includes(id));
    const removed = prevVisibleIds.current.filter(id => !visibleRobotIds.includes(id));

    if (added.length > 0) {
      workerRef.current.postMessage({ type: 'SUBSCRIBE', payload: added });
    }
    if (removed.length > 0) {
      workerRef.current.postMessage({ type: 'UNSUBSCRIBE', payload: removed });
    }

    prevVisibleIds.current = visibleRobotIds;
  }, [visibleRobotIds]);

  return { worker: workerRef.current };
}
