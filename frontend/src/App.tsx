import React from 'react';
import { useTelemetryStore } from '@/store';
import { LoginForm } from '@/components/LoginForm';
import { Dashboard } from '@/components/Dashboard';
import '@/App.css';
/**
 * Main Application Component
 * Handles high-level routing between Authentication and Dashboard.
 */
function App() {
  const { isAuthenticated } = useTelemetryStore();

  return isAuthenticated ? <Dashboard /> : <LoginForm />;
}

export default App;
