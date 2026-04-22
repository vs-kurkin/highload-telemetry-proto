export const UI_CONFIG = {
  // Network - use relative paths to go through Nginx proxy
  API_URL: "/api/",
  WS_URL: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/telemetry/`,

  // Virtual List
  LIST_ITEM_SIZE: 72,
  LIST_HEIGHT: 400,

  // Layout & Charts
  PAPER_HEIGHT: 500,
  CONTAINER_MAX_WIDTH: "lg" as const,
  SPACING: 3,
  MARGIN_Y: 4,

  // Logic Thresholds
  HISTORY_POINTS: 100,
  BATTERY_LOW_THRESHOLD: 20,
  ALERTS_LIMIT: 50,

  // Visuals
  CHART_REFRESH_ANIMATION: false as const,
  CHART_BORDER_COLOR: 'rgb(75, 192, 192)',
} as const;
