import React from 'react';
import { useApi } from '../hooks/useApi';
import { portfolioApi, positionsApi, tradingRunsApi, healthApi } from '../services/api';
import { 
  formatCurrency, formatPercent, formatDateTime, formatRMultiple, getPnlClass, getBadgeClass 
} from '../utils/formatters';

export default function Dashboard() {
  const { data: portfolio, loading: portfolioLoading, refetch: refetchPortfolio } = useApi(
    () => portfolioApi.getSummary(1), [], true
  );
  const { data: positions, loading: positionsLoading } = useApi(
    () => positionsApi.getAll(1, 'OPEN'), [], true
  );
  const { data: runs, loading: runsLoading } = useApi(
    () => tradingRunsApi.getAll(1, 5), [], true
  );
  const { data: health } = useApi(healthApi.check, [], true);

  const openPositions = positions || [];
  const latestRun = runs?.[0];

  const stats = [
    { label: 'Total Equity', value: portfolio?.total_equity, formatter: formatCurrency, positive: true },
    { label: 'Available Cash', value: portfolio?.cash, formatter: formatCurrency },
    { label: 'Invested Value', value: portfolio?.invested_value, formatter: formatCurrency },
    { label: 'Unrealized P&L', value: portfolio?.unrealized_pnl, formatter: formatCurrency, class: getPnlClass(portfolio?.unrealized_pnl) },
    { label: 'Daily P&L', value: portfolio?.daily_pnl, formatter: formatCurrency, class: getPnlClass(portfolio?.daily_pnl) },
    { label: 'Risk Utilization', value: portfolio?.risk_utilization_pct, formatter: (v) => formatPercent(v, 1) },
    { label: 'Daily Loss %', value: portfolio?.daily_loss_pct, formatter: (v) => formatPercent(v, 1), class: getPnlClass(-(portfolio?.daily_loss_pct || 0)) },
    { label: 'Open Positions', value: portfolio?.open_positions_count, formatter: (v) => v },
  ];

  if (portfolioLoading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Portfolio overview & trading status</p>
      </div>

      {health && health.trading_mode === 'DRY_RUN' && (
        <div className="alert alert-warning" style={{ marginBottom: 20 }}>
          ⚠️ Running in DRY RUN mode - No real orders are being placed
        </div>
      )}

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        {stats.map((stat, i) => (
          <div key={i} className="stat-card">
            <div className="stat-label">{stat.label}</div>
            <div className={`stat-value ${stat.class || ''}`}>
              {stat.formatter(stat.value)}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Open Positions</div>
          </div>
          <div className="card-body">
            <div className="table-container">
              {positionsLoading ? (
                <div className="loading"><div className="spinner"></div></div>
              ) : openPositions.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">📭</div>
                  <p>No open positions</p>
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Qty</th>
                      <th>Entry</th>
                      <th>Current</th>
                      <th>Stop</th>
                      <th>Target</th>
                      <th>P&L</th>
                      <th>R</th>
                      <th>Days</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openPositions.map((pos) => (
                      <tr key={pos.id}>
                        <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                        <td>{pos.quantity}</td>
                        <td>{formatCurrency(pos.entry_price)}</td>
                        <td>{pos.current_price ? formatCurrency(pos.current_price) : '-'}</td>
                        <td>{formatCurrency(pos.stop_loss)}</td>
                        <td>{formatCurrency(pos.target_price)}</td>
                        <td className={getPnlClass(pos.unrealized_pnl)}>
                          {formatCurrency(pos.unrealized_pnl)}
                        </td>
                        <td className={`r-multiple ${getPnlClass(pos.r_multiple)}`}>
                          {formatRMultiple(pos.r_multiple)}
                        </td>
                        <td>{pos.holding_days}d</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Latest Trading Run</div>
          </div>
          <div className="card-body">
            {runsLoading ? (
              <div className="loading"><div className="spinner"></div></div>
            ) : latestRun ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span>{formatDateTime(latestRun.run_date)}</span>
                  <span className={`badge ${getBadgeClass(latestRun.status)}`}>{latestRun.status}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, fontSize: 13 }}>
                  <div>
                    <div style={{ color: '#6b7280' }}>Symbols Scanned</div>
                    <div style={{ fontWeight: 600 }}>{latestRun.symbols_scanned}</div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280' }}>Signals Generated</div>
                    <div style={{ fontWeight: 600 }}>{latestRun.signals_generated}</div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280' }}>Orders Filled</div>
                    <div style={{ fontWeight: 600 }}>{latestRun.orders_completed}/{latestRun.orders_attempted}</div>
                  </div>
                </div>
                {latestRun.error_message && (
                  <div className="alert alert-error" style={{ marginTop: 12 }}>
                    {latestRun.error_message}
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">📋</div>
                <p>No trading runs yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Recent Trading Runs</div>
        </div>
        <div className="card-body">
          <div className="table-container">
            {runsLoading ? (
              <div className="loading"><div className="spinner"></div></div>
            ) : !runs || runs.length === 0 ? (
              <div className="empty-state">
                <p>No trading runs recorded</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Scanned</th>
                    <th>Signals</th>
                    <th>Rejected</th>
                    <th>Orders</th>
                    <th>Filled</th>
                    <th>Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {(runs || []).map((run) => (
                    <tr key={run.id}>
                      <td>{formatDateTime(run.run_date)}</td>
                      <td><span className={`badge ${getBadgeClass(run.status)}`}>{run.status}</span></td>
                      <td>{run.symbols_scanned}</td>
                      <td>{run.signals_generated}</td>
                      <td>{run.signals_rejected}</td>
                      <td>{run.orders_attempted}</td>
                      <td>{run.orders_completed}</td>
                      <td><span className={`badge ${run.paper_or_live === 'DRY_RUN' ? 'badge-pending' : 'badge-buy'}`}>{run.paper_or_live}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}