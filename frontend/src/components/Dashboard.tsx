import React, { useState, useMemo, useEffect, useCallback, useTransition } from 'react';
import { useTelemetryStore } from '@/store';
import { useTelemetryWS } from '@/useTelemetryWS';
import { 
  Container, Typography, Box, Paper, 
  Grid, Button, TextField, InputAdornment, Chip, Divider, CssBaseline
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { FixedSizeList as VirtualList, type ListOnItemsRenderedProps } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { Line } from 'react-chartjs-2';
import { UI_CONFIG } from '@/config';
import { RobotRow } from '@/components/RobotRow';
import { AlertItem } from '@/components/AlertItem';

export const Dashboard: React.FC = () => {
  const { 
    robots, robotIds, alerts, wsConnected, logout, fetchInitialData, 
    resolveAlert, fetchHistoricalStats, selectedRobotId, selectRobot, 
    dataVersion, setVisibleRobots
  } = useTelemetryStore();

  const [search, setSearch] = useState("");
  const [deferredSearch, setDeferredSearch] = useState("");
  const [isPending, startTransition] = useTransition();

  useTelemetryWS();

  const filteredIds = useMemo(() => {
    if (!deferredSearch) return robotIds;
    const lowerSearch = deferredSearch.toLowerCase();
    return robotIds.filter(id => id.toLowerCase().includes(lowerSearch));
  }, [robotIds, deferredSearch]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearch(value); // High priority: update input field immediately
    startTransition(() => {
      setDeferredSearch(value); // Lower priority: update list later
    });
  };

  useEffect(() => {
    fetchInitialData();
    fetchHistoricalStats();
    const syncInterval = setInterval(fetchInitialData, 30000);
    return () => clearInterval(syncInterval);
  }, [fetchInitialData, fetchHistoricalStats]);

  const handleItemsRendered = useCallback(({ visibleStartIndex, visibleStopIndex }: ListOnItemsRenderedProps) => {
    const visibleIds = filteredIds.slice(visibleStartIndex, visibleStopIndex + 1);
    if (selectedRobotId && !visibleIds.includes(selectedRobotId)) {
      visibleIds.push(selectedRobotId);
    }
    setVisibleRobots(visibleIds);
  }, [filteredIds, selectedRobotId, setVisibleRobots]);

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
                Inventory: <strong>{robotIds.length}</strong>
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
                  onChange={handleSearchChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" sx={{ color: isPending ? 'primary.main' : 'inherit' }} />
                      </InputAdornment>
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
                      onItemsRendered={handleItemsRendered}
                      itemData={{ 
                        ids: filteredIds, 
                        robots, 
                        selectedId: selectedRobotId, 
                        onSelect: selectRobot,
                        dataVersion
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
                    key={selectedRobotId}
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
                      animation: {
                        duration: 100,
                        easing: 'linear'
                      },
                      scales: { 
                        y: { min: 0, max: 100, display: true, ticks: { font: { size: 10 } } },
                        x: { display: false }
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
};
