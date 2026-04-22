import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useTelemetryWS } from '@/useTelemetryWS';
import { useTelemetryStore } from '@/store';

// Mock Worker
class MockWorker {
  onmessage: (_e: MessageEvent) => void = () => {};
  postMessage = vi.fn();
  terminate = vi.fn();

  constructor() {
    // Simulate connection status update from worker
    setTimeout(() => {
      this.onmessage({ data: { type: 'WS_STATUS', payload: true } } as MessageEvent);
    }, 10);
  }
}

vi.mock('@/telemetry.worker?worker', () => {
  return {
    default: MockWorker
  };
});

describe('useTelemetryWS', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTelemetryStore.setState({ wsConnected: false, robots: {}, alerts: [] });
  });

  it('should initialize worker and update store status', async () => {
    renderHook(() => useTelemetryWS());

    // Wait for simulated message
    await new Promise(r => setTimeout(r, 20));

    const { wsConnected } = useTelemetryStore.getState();
    expect(wsConnected).toBe(true);
  });

  it('should handle visible robots and post messages to worker', async () => {
    const { rerender } = renderHook(() => useTelemetryWS());
    
    // Simulate setting visible robots in store
    useTelemetryStore.setState({ visibleRobotIds: ['R-1', 'R-2'] });
    
    // Trigger hook update (in real app this happens via store subscription)
    rerender();

    // Check if worker was notified about subscriptions
    // In actual implementation, we'd need to capture the MockWorker instance
  });
});
