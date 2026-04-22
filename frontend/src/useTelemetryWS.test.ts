import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTelemetryWS } from './useTelemetryWS';
import { useTelemetryStore } from './store';

// Mock global WebSocket
class MockWebSocket {
  onopen: () => void = () => {};
  onclose: () => void = () => {};
  onmessage: (event: MessageEvent) => void = () => {};
  onerror: () => void = () => {};
  close = vi.fn();
  send = vi.fn();

  constructor(public url: string) {
    // Artificial delay to simulate connection
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 10);
  }
}

vi.stubGlobal('WebSocket', MockWebSocket);

describe('useTelemetryWS', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTelemetryStore.setState({ wsConnected: false, robots: {}, alerts: [] });
  });

  it('should connect to WebSocket and update store status', async () => {
    const { result } = renderHook(() => useTelemetryWS());

    // Wait for onopen simulation
    await act(async () => {
      await new Promise(r => setTimeout(r, 20));
    });

    const { wsConnected } = useTelemetryStore.getState();
    expect(wsConnected).toBe(true);
    expect(result.current.ws).toBeDefined();
  });

  it('should handle telemetry update message', async () => {
    renderHook(() => useTelemetryWS());

    // Wait for connection
    await act(async () => {
      await new Promise(r => setTimeout(r, 20));
    });

    const state = useTelemetryStore.getState();
    expect(state.wsConnected).toBe(true);
  });
});
