import React, { useState, useMemo, useEffect } from 'react';
import { useTelemetryStore, type AlertData } from './store';
import { useTelemetryWS } from './useTelemetryWS';
import { 
  Container, Typography, Box, Paper, ListItemButton, 
  Grid, LinearProgress, Alert, Button,
  TextField, InputAdornment, Chip, Divider, CssBaseline,
  Collapse
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { FixedSizeList as VirtualList } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { UI_CONFIG } from './config';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface RobotRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    ids: string[];
    robots: Record<string, { battery: number; status: string }>;
    selectedId: string | null;
    onSelect: (id: string) => void;
    version: number;
  };
}

const RobotRow: React.FC<RobotRowProps> = React.memo(({ index, style, data }) => {
  const robotId = data.ids[index];
  const robot = data.robots[robotId];
  const isSelected = data.selectedId === robotId;

  if (!robot) return <div style={style} />;

  return (
    <div style={style}>
      <ListItemButton 
        divider 
        onClick={() => data.onSelect(robotId)}
        sx={{ 
          height: '100%',
          bgcolor: isSelected ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
          '&:hover': {
            bgcolor: isSelected ? 'rgba(25, 118, 210, 0.12)' : 'rgba(0, 0, 0, 0.04)',
            cursor: 'pointer'
          },
          transition: 'background-color 0.1s',
          borderLeft: isSelected ? '4px solid #1976d2' : '4px solid transparent',
          px: 1
        }}
      >
        <Grid container alignItems="center">
          <Grid item xs={3}>
            <Typography variant="subtitle2" sx={{ fontWeight: isSelected ? 800 : 500, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {robotId}
            </Typography>
          </Grid>
          <Grid item xs={6} sx={{ px: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box sx={{ width: '100%', mr: 1 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={isNaN(robot.battery) ? 0 : robot.battery} 
                  color={robot.battery < UI_CONFIG.BATTERY_LOW_THRESHOLD ? "error" : "primary"}
                  sx={{ height: 6, borderRadius: 3 }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ minWidth: 25 }}>
                {isNaN(robot.battery) ? '0%' : `${Math.round(robot.battery)}%`}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={3} sx={{ textAlign: 'right' }}>
            <Chip 
              label={robot.status} 
              size="small"
              color={robot.status === 'OK' ? 'success' : (robot.status === 'CHARGING' ? 'info' : 'error')}
              variant={isSelected ? "filled" : "outlined"}
              sx={{ height: 20, fontSize: '0.65rem', fontWeight: 'bold' }}
            />
          </Grid>
        </Grid>
      </ListItemButton>
    </div>
  );
});

const AlertItem: React.FC<{ alert: AlertData, onResolve: (id: number) => void }> = ({ alert, onResolve }) => {
  const [visible, setVisible] = useState(true);

  const handleFix = () => {
    setVisible(false);
    onResolve(alert.id);
  };

  return (
    <Collapse in={visible} timeout={300}>
      <Alert 
        severity="error" 
        sx={{ mb: 1, borderRadius: 2 }}
        action={
          <Button color="error" size="small" variant="text" onClick={handleFix} sx={{ fontWeight: 'bold' }}>FIX</Button>
        }
      >
        <strong>{alert.robot_id}</strong>: {alert.message}
      </Alert>
    </Collapse>
  );
};

function DashboardContent() {
  const { 
    robots, alerts, wsConnected, logout, fetchInitialData, 
    resolveAlert, fetchHistoricalStats, selectedRobotId, selectRobot, dataVersion
  } = useTelemetryStore();

  const [search, setSearch] = useState("");
  useTelemetryWS();

  const filteredIds = useMemo(() => {
    return Object.keys(robots)
      .filter(id => id.toLowerCase().includes(search.toLowerCase()))
      .sort();
  }, [robots, search]);

  useEffect(() => {
    fetchInitialData();
    fetchHistoricalStats();
    const syncInterval = setInterval(() => {
      fetchInitialData();
    }, 10000);
    return () => clearInterval(syncInterval);
  }, [fetchInitialData, fetchHistoricalStats]);

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh', 
      bgcolor: '#f8f9fa',
      overflow: 'hidden' 
    }}>
      <CssBaseline />

      <Paper elevation={0} sx={{ p: 2, borderRadius: 0, zIndex: 1100, borderBottom: '1px solid #e0e0e0' }}>
        <Container maxWidth={UI_CONFIG.CONTAINER_MAX_WIDTH}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Typography variant="h5" sx={{ fontWeight: 900, letterSpacing: -1, color: '#1a237e' }}>
                FLEET CONTROL PANEL
              </Typography>
              <Chip 
                label={wsConnected ? "CONNECTION: ACTIVE" : "CONNECTION: LOST"}
                color={wsConnected ? "success" : "error"}
                size="small"
                sx={{ fontWeight: 'bold', height: 24, borderRadius: 1 }}
              />
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Robots: <strong>{filteredIds.length}</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Events: <strong>{alerts.length}</strong>
              </Typography>
              <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
              <Button variant="outlined" size="small" color="inherit" onClick={logout} sx={{ borderRadius: 2 }}>Logout</Button>
            </Box>
          </Box>
        </Container>
      </Paper>

      <Container maxWidth={UI_CONFIG.CONTAINER_MAX_WIDTH} sx={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 2, 
        py: 2,
        overflow: 'hidden'
      }}>
        <Grid container spacing={2} sx={{ flex: 1, overflow: 'hidden' }}>
          <Grid item xs={12} md={4} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Paper elevation={0} sx={{ 
              p: 2, 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column', 
              overflow: 'hidden',
              borderRadius: 3,
              border: '1px solid #e0e0e0'
            }}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1.5 }}>Fleet Inventory</Typography>
                <TextField 
                  fullWidth
                  size="small"
                  placeholder="Filter by ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>
                    ),
                    sx: { borderRadius: 2, bgcolor: '#f1f3f4', '& fieldset': { border: 'none' } }
                  }}
                />
              </Box>
              <Box sx={{ flex: 1, minHeight: 0 }}>
                <AutoSizer>
                  {({ height, width }: { height: number; width: number }) => (
                    <VirtualList
                      height={height}
                      itemCount={filteredIds.length}
                      itemSize={60}
                      width={width}
                      itemData={{ 
                        ids: filteredIds, 
                        robots, 
                        selectedId: selectedRobotId, 
                        onSelect: selectRobot,
                        version: dataVersion // Force list re-render
                      }}
                    >
                      {RobotRow}
                    </VirtualList>
                  )}
                </AutoSizer>
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} md={8} sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Paper elevation={0} sx={{ p: 2, borderRadius: 3, border: '1px solid #e0e0e0' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
                Real-time Monitor: <span style={{ color: '#1976d2' }}>{selectedRobotId || 'Select a device'}</span>
              </Typography>
              <Box sx={{ height: 200 }}>
                {selectedRobotId && robots[selectedRobotId] ? (
                  <Line
                    data={{
                      labels: Array.from({ length: robots[selectedRobotId].history.length }, (_, i) => i),
                      datasets: [{
                        label: `Battery`,
                        data: robots[selectedRobotId].history,
                        borderColor: '#1976d2',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        tension: 0,
                        fill: true,
                        pointRadius: 0
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      // Match animation duration to throttle interval for maximum smoothness
                      animation: {
                        duration: 100,
                        easing: 'linear'
                      },
                      scales: { 
                        y: { 
                          min: 0, 
                          max: 100, 
                          display: true, 
                          ticks: { font: { size: 10 } } 
                        },
                        x: { display: false }
                      },
                      elements: {
                        line: {
                          borderWidth: 2
                        },
                        point: {
                          radius: 0
                        }
                      },
                      plugins: { 
                        legend: { display: false },
                        tooltip: { enabled: false }
                      }
                    }}
                  />
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', opacity: 0.4 }}>
                    <Typography variant="body2">No device selected for monitoring</Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            <Paper elevation={0} sx={{ 
              p: 2, 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column', 
              overflow: 'hidden',
              borderRadius: 3,
              border: '1px solid #e0e0e0'
            }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
                Security Events {alerts.length > 0 && `(${alerts.length})`}
              </Typography>
              <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
                {alerts.length > 0 ? (
                  alerts.map((a) => (
                    <AlertItem key={a.id} alert={a} onResolve={resolveAlert} />
                  ))
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', opacity: 0.3 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>SYSTEM SECURE: NO THREATS</Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
function App() {
  const { isAuthenticated, login } = useTelemetryStore();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin_password");

  if (!isAuthenticated) {
    return (
      <Box sx={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: '#f1f3f4'
      }}>
        <CssBaseline />
        <Container maxWidth="xs">
          <Paper elevation={0} sx={{ p: 5, borderRadius: 5, border: '1px solid #e0e0e0', textAlign: 'center' }}>
            <Typography variant="h4" sx={{ mb: 1, fontWeight: 900, letterSpacing: -1.5 }}>FLEET LOGIN</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>Control Panel Authentication</Typography>
            <form onSubmit={async (e) => { e.preventDefault(); await login(username, password); }}>
              <TextField 
                fullWidth label="Username" margin="normal" variant="filled"
                InputProps={{ sx: { borderRadius: 2, '&:before, &:after': { display: 'none' } } }}
                value={username} onChange={e => setUsername(e.target.value)} 
              />
              <TextField 
                fullWidth label="Password" type="password" margin="normal" variant="filled"
                InputProps={{ sx: { borderRadius: 2, '&:before, &:after': { display: 'none' } } }}
                value={password} onChange={e => setPassword(e.target.value)} 
              />
              <Button 
                fullWidth variant="contained" size="large" type="submit" 
                sx={{ mt: 4, py: 2, borderRadius: 3, fontWeight: 900, fontSize: '1rem', boxShadow: 'none' }}
              >
                SIGN IN
              </Button>
            </form>
          </Paper>
        </Container>
      </Box>
    );
  }
  return <DashboardContent />;
}

export default App;
