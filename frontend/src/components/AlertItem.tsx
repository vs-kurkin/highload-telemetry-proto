import React, { useState } from 'react';
import { Alert, Button, Collapse } from '@mui/material';
import { type AlertData } from '@/store';

interface AlertItemProps {
  alert: AlertData;
  onResolve: (id: number) => void;
}

export const AlertItem: React.FC<AlertItemProps> = ({ alert, onResolve }) => {
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
