/**
 * Telemetry Web Worker
 * Handles WebSocket connection and JSON parsing off the main thread.
 */

interface TelemetryData {
  battery: number;
  status: string;
}

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let updateBuffer: Record<string, TelemetryData> = {};
let lastFlush = 0;
const FLUSH_INTERVAL = 100; // ms

function connect(url: string) {
  if (socket) socket.close();
  
  socket = new WebSocket(url);

  socket.onopen = () => {
    self.postMessage({ type: 'WS_STATUS', payload: true });
  };

  socket.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      
      if (data.type === 'alert') {
        self.postMessage({ type: 'ALERT', payload: data.payload });
      } else if (data.type === 'telemetry_update') {
        // Merge into buffer
        Object.assign(updateBuffer, data.data);
        scheduleFlush();
      } else if (typeof data === 'object' && !data.type) {
        // Raw map support
        Object.assign(updateBuffer, data);
        scheduleFlush();
      }
    } catch (_e) {
      // Ignore parse errors
    }
  };

  socket.onclose = () => {
    self.postMessage({ type: 'WS_STATUS', payload: false });
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => connect(url), 3000);
  };

  socket.onerror = () => {
    socket?.close();
  };
}

function scheduleFlush() {
  const now = Date.now();
  if (now - lastFlush >= FLUSH_INTERVAL) {
    flush();
  } else {
    // Already scheduled or too early, but we could use a timeout if not already pending
    // For simplicity, we'll just flush on next message if interval passed
  }
}

function flush() {
  if (Object.keys(updateBuffer).length > 0) {
    self.postMessage({ type: 'TELEMETRY_BATCH', payload: updateBuffer });
    updateBuffer = {};
    lastFlush = Date.now();
  }
}

// Periodical flush for low-frequency updates
setInterval(flush, FLUSH_INTERVAL);

self.onmessage = (e) => {
  const { type, payload } = e.data;
  
  switch (type) {
    case 'CONNECT':
      connect(payload);
      break;
    case 'SUBSCRIBE':
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'subscribe', robots: payload }));
      }
      break;
    case 'UNSUBSCRIBE':
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'unsubscribe', robots: payload }));
      }
      break;
  }
};
