import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PositionsPage from './pages/PositionsPage';
import SignalsPage from './pages/SignalsPage';
import TradingRunsPage from './pages/TradingRunsPage';
import LogsPage from './pages/LogsPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="positions" element={<PositionsPage />} />
        <Route path="signals" element={<SignalsPage />} />
        <Route path="trading-runs" element={<TradingRunsPage />} />
        <Route path="logs" element={<LogsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;