export const MOCK_TELEMETRY_UPDATE = {
  "R-123": { battery: 85.5, status: "OK" },
  "R-456": { battery: 10.0, status: "WARNING" }
};

export const MOCK_ALERT = {
  id: 1,
  robot_id: "R-123",
  message: "Low battery: 5.0%",
  battery: 5.0
};

export const INITIAL_STATE = {
  robots: {},
  alerts: [],
  wsConnected: false,
  connectionError: null,
};
