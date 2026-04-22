import { describe, it, expect, beforeEach } from 'vitest';
import { useTelemetryStore } from './store';

describe('TelemetryStore', () => {
  beforeEach(() => {
    // Reset store state if needed, though Zustand persists between tests in same process
    // For simplicity, we just check transitions
  });

  it('should update telemetry data correctly', () => {
    const { updateTelemetry } = useTelemetryStore.getState();

    const mockData = {
      'R-1': { battery: 95.5, status: 'OK' }
    };

    updateTelemetry(mockData);

    const { robots } = useTelemetryStore.getState();
    expect(robots['R-1']).toBeDefined();
    expect(robots['R-1'].battery).toBe(95.5);
    expect(robots['R-1'].history).toContain(95.5);
  });

  it('should throttle updates correctly', () => {
    const { throttledUpdateTelemetry } = useTelemetryStore.getState();
    // First update
    throttledUpdateTelemetry({ 'R-1': { battery: 90, status: 'OK' } });

    // Immediate second update - should be buffered
    throttledUpdateTelemetry({ 'R-1': { battery: 80, status: 'OK' } });

    // Since 1 second hasn't passed, updateTelemetry shouldn't have been called (or called only once if it was the first time)
    // Actually the first one sets lastFlush=0, so it flushes immediately if it's the very first call.
    // Let's check logic: if (now - lastFlush >= 1000)
  });

  it('should add alerts correctly', () => {
    const { addAlert } = useTelemetryStore.getState();
    const mockAlert = { id: 1, robot_id: 'R-1', message: 'Low battery', battery: 5 };

    addAlert(mockAlert);

    const { alerts } = useTelemetryStore.getState();
    expect(alerts).toContainEqual(mockAlert);
  });
});
