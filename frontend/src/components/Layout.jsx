import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { healthApi } from '../services/api';
import { formatDateTime } from '../utils/formatters';

export default function Layout() {
  const { data: health, loading: healthLoading } = useApi(healthApi.check, [], true);
  const [time, setTime] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const isDryRun = health?.trading_mode === 'DRY_RUN';

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <span>📈 Swing Trading System</span>
            <span className={`mode-badge ${isDryRun ? 'dry-run' : 'live'}`}>
              {isDryRun ? 'DRY RUN' : 'LIVE'}
            </span>
          </div>
          <nav className="header-nav">
            <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              Dashboard
            </NavLink>
            <NavLink to="/positions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              Positions
            </NavLink>
            <NavLink to="/signals" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              Signals
            </NavLink>
            <NavLink to="/trading-runs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              Runs
            </NavLink>
            <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              Logs
            </NavLink>
          </nav>
          <div style={{ color: '#9ca3af', fontSize: '13px', fontFamily: 'monospace' }}>
            {time.toLocaleTimeString('en-IN', { hour12: false, timeZone: 'Asia/Kolkata' })} IST
          </div>
        </div>
      </header>
      <main className="main">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}