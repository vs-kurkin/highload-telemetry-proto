import { describe, it, expect, beforeEach } from 'vitest';
import { useTelemetryStore } from '@/store';

describe('TelemetryStore', () => {
  beforeEach(() => {
    useTelemetryStore.setState({ 
      robots: {}, 
      robotIds: [], 
      alerts: [],
      dataVersion: 0 
    });
  });

  it('should initialize with inventory correctly', async () => {
    // Manually set inventory for testing batch updates
    useTelemetryStore.setState({
      robots: { 'R-1': { battery: 0, status: 'OK', history: [] } },
      robotIds: ['R-1']
    });

    const mockData = {
      'R-1': { battery: 95.5, status: 'OK' }
    };

    useTelemetryStore.getState().updateTelemetryBatch(mockData);

    const { robots } = useTelemetryStore.getState();
    expect(robots['R-1']).toBeDefined();
    expect(robots['R-1'].battery).toBe(95.5);
    expect(robots['R-1'].history).toContain(95.5);
  });

  it('should correctly manage history with circular updates', () => {
    useTelemetryStore.setState({
      robots: { 'R-1': { battery: 0, status: 'OK', history: new Array(100).fill(50) } },
      robotIds: ['R-1']
    });

    const { updateTelemetryBatch } = useTelemetryStore.getState();
    
    updateTelemetryBatch({ 'R-1': { battery: 100, status: 'OK' } });

    const { robots } = useTelemetryStore.getState();
    expect(robots['R-1'].history.length).toBe(100);
    expect(robots['R-1'].history[99]).toBe(100);
    expect(robots['R-1'].history[0]).toBe(50);
  });

  it('should add alerts correctly', () => {
    const { addAlert } = useTelemetryStore.getState();
    const mockAlert = { id: 1, robot_id: 'R-1', message: 'Low battery', battery: 5 };

    addAlert(mockAlert);

    const { alerts } = useTelemetryStore.getState();
    expect(alerts).toContainEqual(mockAlert);
  });
});
