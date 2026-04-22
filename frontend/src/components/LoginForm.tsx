import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button, Container, CssBaseline } from '@mui/material';
import { useTelemetryStore } from '@/store';

export const LoginForm: React.FC = () => {
  const { login } = useTelemetryStore();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin_password");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

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
          <form onSubmit={handleSubmit}>
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
};
