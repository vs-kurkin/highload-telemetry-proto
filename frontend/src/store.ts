import { create } from 'zustand';
import { UI_CONFIG } from './config';
import throttle from 'lodash.throttle';

interface RobotData {
  battery: number;
  status: string;
  history: number[];
}

export interface AlertData {
  id: number;
  robot_id: string;
  message: string;
  battery: number;
  created_at?: string;
}

interface DailyStat {
  robot_id: string;
  date: string;
  avg_battery: number;
  min_battery: number;
  max_battery: number;
  message_count: number;
}

interface APIRobot {
  robot_id: string;
  status: string;
}

interface APIAlert {
  id: number;
  robot_id: string;
  message: string;
  created_at: string;
  is_resolved: boolean;
}

interface TelemetryStore {
  robots: Record<string, RobotData>;
  alerts: AlertData[];
  wsConnected: boolean;
  historicalStats: DailyStat[];
  isAuthenticated: boolean;
  selectedRobotId: string | null;
  dataVersion: number;
  setWsStatus: (status: boolean) => void;
  selectRobot: (id: string | null) => void;
  updateTelemetry: (data: Record<string, { battery: number, status: string }>) => void;
  throttledUpdateTelemetry: (data: Record<string, { battery: number, status: string }>) => void;
  addAlert: (alert: AlertData) => void;
  resolveAlert: (id: number) => Promise<void>;
  fetchInitialData: () => Promise<void>;
  fetchHistoricalStats: (robotId?: string) => Promise<void>;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

let updateBuffer: Record<string, { battery: number, status: string }> = {};

export const useTelemetryStore = create<TelemetryStore>((set, get) => ({
  robots: {},
  alerts: [],
  wsConnected: false,
  historicalStats: [],
  isAuthenticated: sessionStorage.getItem('is_auth') === 'true',
  selectedRobotId: null,
  dataVersion: 0,
  setWsStatus: (status) => set({ wsConnected: status }),
  selectRobot: (id) => set({ selectedRobotId: id }),
  updateTelemetry: (data) => set((state) => {
    const newRobots = { ...state.robots };
    let hasChanges = false;

    Object.entries(data).forEach(([rid, info]) => {
      const current = newRobots[rid] || { battery: 0, status: 'OK', history: [] };
      let oldHistory = Array.isArray(current.history) ? current.history : [];

      if (oldHistory.length === 0) {
        oldHistory = new Array(UI_CONFIG.HISTORY_POINTS).fill(info.battery);
      }

      const newHistory = [...oldHistory, info.battery].slice(-UI_CONFIG.HISTORY_POINTS);

      newRobots[rid] = {
        battery: info.battery,
        status: info.status,
        history: newHistory
      };
      hasChanges = true;
    });

    return hasChanges ? {
      robots: newRobots,
      dataVersion: state.dataVersion + 1
    } : state;
  }),
  throttledUpdateTelemetry: throttle((data) => {
    updateBuffer = { ...updateBuffer, ...data };
    get().updateTelemetry(updateBuffer);
    updateBuffer = {};
  }, 100),
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, UI_CONFIG.ALERTS_LIMIT)
  })),
  login: async (username, password) => {
    try {
      const response = await fetch(`${UI_CONFIG.API_URL}token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        sessionStorage.setItem('is_auth', 'true');
        set({ isAuthenticated: true });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },
  logout: () => {
    sessionStorage.removeItem('is_auth');
    set({ isAuthenticated: false, robots: {}, alerts: [] });
  },
  resolveAlert: async (id) => {
    try {
      const response = await fetch(`${UI_CONFIG.API_URL}alerts/${id}/resolve/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      if (response.ok) {
        setTimeout(() => {
          set((state) => ({
            alerts: state.alerts.filter(a => a.id !== id)
          }));
        }, 300);
      }
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  },
  fetchInitialData: async () => {
    try {
      const [robotsRes, alertsRes] = await Promise.all([
        fetch(`${UI_CONFIG.API_URL}robots/`, { credentials: 'include' }),
        fetch(`${UI_CONFIG.API_URL}alerts/`, { credentials: 'include' })
      ]);

      if (robotsRes.ok && alertsRes.ok) {
        const robotsData: APIRobot[] = await robotsRes.json();
        const alertsData: APIAlert[] = await alertsRes.json();

        set((state) => {
          const newRobots = { ...state.robots };
          if (Array.isArray(robotsData)) {
            robotsData.forEach((r) => {
              if (r && r.robot_id && !newRobots[r.robot_id]) {
                newRobots[r.robot_id] = {
                  battery: 0,
                  status: r.status || 'UNKNOWN',
                  history: []
                };
              }
            });
          }

          return {
            robots: newRobots,
            dataVersion: state.dataVersion + 1,
            alerts: Array.isArray(alertsData) ? alertsData.map(a => ({
              id: a.id,
              robot_id: a.robot_id || 'UNKNOWN',
              message: a.message || '',
              battery: 0,
              created_at: a.created_at
            })) : []
          };
        });
      } else if (robotsRes.status === 401) {
        sessionStorage.removeItem('is_auth');
        set({ isAuthenticated: false });
      }
    } catch (error) {
      console.error('Failed to fetch initial data:', error);
    }
  },
  fetchHistoricalStats: async (robotId) => {
    try {
      const url = robotId
        ? `${UI_CONFIG.API_URL}stats/?robot_id=${robotId}`
        : `${UI_CONFIG.API_URL}stats/`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const data: DailyStat[] = await res.json();
        set({ historicalStats: data });
      }
    } catch (error) {
      console.error('Failed to fetch historical stats:', error);
    }
  }
}));
