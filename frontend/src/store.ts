import { create } from 'zustand';
import { UI_CONFIG } from '@/config';

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

// Optimized fetch wrapper with automatic token refresh
async function apiFetch(url: string, options: RequestInit = {}) {
  const defaultOptions = {
    ...options,
    credentials: 'include' as const,
    headers: {
      ...options.headers,
      'Content-Type': 'application/json',
    },
  };

  let response = await fetch(url, defaultOptions);

  if (response.status === 401 && !url.includes('token/refresh')) {
    // Try to refresh token
    const refreshRes = await fetch(`${UI_CONFIG.API_URL}token/refresh/`, {
      method: 'POST',
      credentials: 'include',
    });

    if (refreshRes.ok) {
      // Retry original request
      response = await fetch(url, defaultOptions);
    } else {
      // Refresh failed, logout
      sessionStorage.removeItem('is_auth');
      window.location.reload();
    }
  }

  return response;
}

interface TelemetryStore {
  robots: Record<string, RobotData>;
  robotIds: string[]; // Separated for O(1) checks and efficient list rendering
  alerts: AlertData[];
  wsConnected: boolean;
  historicalStats: DailyStat[];
  isAuthenticated: boolean;
  selectedRobotId: string | null;
  visibleRobotIds: string[]; // For WS subscriptions
  dataVersion: number;
  
  setWsStatus: (_status: boolean) => void;
  selectRobot: (_id: string | null) => void;
  setVisibleRobots: (_ids: string[]) => void;
  updateTelemetryBatch: (_data: Record<string, { battery: number, status: string }>) => void;
  addAlert: (_alert: AlertData) => void;
  resolveAlert: (_id: number) => Promise<void>;
  fetchInitialData: () => Promise<void>;
  fetchHistoricalStats: (_robotId?: string) => Promise<void>;
  login: (_username: string, _password: string) => Promise<boolean>;
  logout: () => void;
}

export const useTelemetryStore = create<TelemetryStore>((set, get) => ({
  robots: {},
  robotIds: [],
  alerts: [],
  wsConnected: false,
  historicalStats: [],
  isAuthenticated: sessionStorage.getItem('is_auth') === 'true',
  selectedRobotId: null,
  visibleRobotIds: [],
  dataVersion: 0,

  setWsStatus: (status) => set({ wsConnected: status }),
  selectRobot: (id) => set({ selectedRobotId: id }),
  
  setVisibleRobots: (ids) => {
    const prev = get().visibleRobotIds;
    // Simple equality check to avoid redundant updates
    if (prev.length === ids.length && ids.every((v, i) => v === prev[i])) return;
    set({ visibleRobotIds: ids });
  },

  updateTelemetryBatch: (data) => set((state) => {
    const newRobots = { ...state.robots };
    let hasChanges = false;

    for (const rid in data) {
      const info = data[rid];
      const current = newRobots[rid];
      if (!current) continue;

      // Circular buffer-like update without creating a new array reference every time
      // unless we want to trigger a re-render of components observing this specific robot.
      // Since RobotRow is memoized and depends on robot object reference, 
      // we DO need a new object, but we can optimize the history array.
      
      const oldHistory = current.history;
      let newHistory: number[];
      
      if (oldHistory.length < UI_CONFIG.HISTORY_POINTS) {
        newHistory = [...oldHistory, info.battery];
      } else {
        // Reuse most of the array
        newHistory = oldHistory.slice(1);
        newHistory.push(info.battery);
      }

      newRobots[rid] = {
        battery: info.battery,
        status: info.status,
        history: newHistory
      };
      hasChanges = true;
    }

    return hasChanges ? {
      robots: newRobots,
      dataVersion: state.dataVersion + 1
    } : state;
  }),

  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, UI_CONFIG.ALERTS_LIMIT)
  })),

  login: async (username, password) => {
    try {
      const response = await fetch(`${UI_CONFIG.API_URL}token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include'
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
    set({ isAuthenticated: false, robots: {}, robotIds: [], alerts: [] });
  },

  resolveAlert: async (id) => {
    try {
      const response = await apiFetch(`${UI_CONFIG.API_URL}alerts/${id}/resolve/`, {
        method: 'POST'
      });
      if (response.ok) {
        set((state) => ({
          alerts: state.alerts.filter(a => a.id !== id)
        }));
      }
    } catch (_error) {
      // Error is handled by not resolving the alert in UI
    }
  },

  fetchInitialData: async () => {
    try {
      const [robotsRes, alertsRes] = await Promise.all([
        apiFetch(`${UI_CONFIG.API_URL}robots/`),
        apiFetch(`${UI_CONFIG.API_URL}alerts/`)
      ]);

      if (robotsRes.ok && alertsRes.ok) {
        const robotsData: APIRobot[] = await robotsRes.json();
        const alertsData: APIAlert[] = await alertsRes.json();

        set((state) => {
          const newRobots = { ...state.robots };
          const newIds: string[] = [];
          
          robotsData.forEach((r) => {
            newIds.push(r.robot_id);
            if (!newRobots[r.robot_id]) {
              newRobots[r.robot_id] = {
                battery: 0,
                status: r.status || 'UNKNOWN',
                history: []
              };
            }
          });

          return {
            robots: newRobots,
            robotIds: newIds.sort(),
            dataVersion: state.dataVersion + 1,
            alerts: alertsData.map(a => ({
              id: a.id,
              robot_id: a.robot_id,
              message: a.message,
              battery: 0,
              created_at: a.created_at
            }))
          };
        });
      }
    } catch (_error) {
      // Error handled by empty initial state
    }
  },

  fetchHistoricalStats: async (robotId) => {
    try {
      const url = robotId
        ? `${UI_CONFIG.API_URL}stats/?robot_id=${robotId}`
        : `${UI_CONFIG.API_URL}stats/`;
      const res = await apiFetch(url);
      if (res.ok) {
        const data: DailyStat[] = await res.json();
        set({ historicalStats: data });
      }
    } catch (_error) {
      // Error handled by not updating stats
    }
  }
}));

