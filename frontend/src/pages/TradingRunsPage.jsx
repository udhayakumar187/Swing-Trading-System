import React from 'react';
import { useApi } from '../hooks/useApi';
import { tradingRunsApi } from '../services/api';
import { formatDateTime, getBadgeClass } from '../utils/formatters';

export default function TradingRunsPage() {
  const { data: runs, loading, refetch } = useApi(
    () => tradingRunsApi.getAll(1, 100), 
    [], 
    true
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Trading Runs</h1>
        <p className="page-subtitle">Historical daily trading execution runs</p>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            {loading ? (
              <div className="loading"><div className="spinner"></div></div>
            ) : !runs?.length ? (
              <div className="empty-state">
                <div className="empty-state-icon">📋</div>
                <p>No trading runs recorded</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Run Date</th>
                    <th>Status</th>
                    <th>Scanned</th>
                    <th>Signals</th>
                    <th>Rejected</th>
                    <th>Orders</th>
                    <th>Filled</th>
                    <th>Rejected</th>
                    <th>Completed</th>
                    <th>Mode</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>{formatDateTime(run.run_date)}</td>
                      <td><span className={`badge ${getBadgeClass(run.status)}`}>{run.status}</span></td>
                      <td>{run.symbols_scanned}</td>
                      <td>{run.signals_generated}</td>
                      <td>{run.signals_rejected}</td>
                      <td>{run.orders_attempted}</td>
                      <td>{run.orders_completed}</td>
                      <td>{run.orders_rejected}</td>
                      <td>{run.completed_at ? formatDateTime(run.completed_at) : '-'}</td>
                      <td><span className={`badge ${run.paper_or_live === 'DRY_RUN' ? 'badge-pending' : 'badge-buy'}`}>{run.paper_or_live}</span></td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, color: run.error_message ? '#dc2626' : '#6b7280' }}>
                        {run.error_message || '-'}
                      </td>
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