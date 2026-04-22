import React from 'react';
import { Typography, Box, ListItemButton, Grid, LinearProgress, Chip } from '@mui/material';
import { UI_CONFIG } from '@/config';

interface RobotRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    ids: string[];
    robots: Record<string, { battery: number; status: string }>;
    selectedId: string | null;
    onSelect: (id: string) => void;
    dataVersion: number;
  };
}

export const RobotRow: React.FC<RobotRowProps> = React.memo(({ index, style, data }) => {
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
