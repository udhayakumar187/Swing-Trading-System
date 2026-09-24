import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { positionsApi, portfolioApi } from '../services/api';
import { 
  formatCurrency, formatDateTime, formatRMultiple, getPnlClass, getBadgeClass 
} from '../utils/formatters';

export default function PositionsPage() {
  const [statusFilter, setStatusFilter] = useState('');
  
  const { data: positions, loading, refetch } = useApi(
    () => positionsApi.getAll(1, statusFilter || undefined), 
    [statusFilter], 
    true
  );

  const statusOptions = ['', 'OPEN', 'CLOSED', 'STOPPED_OUT', 'TARGET_HIT', 'MANUALLY_CLOSED'];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Positions</h1>
        <p className="page-subtitle">View and manage all positions</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14, color: '#6b7280' }}>Filter:</span>
            {statusOptions.map((status) => (
              <button
                key={status}
                className={`btn ${statusFilter === status ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: 13 }}
                onClick={() => setStatusFilter(status)}
              >
                {status || 'All'}
              </button>
            ))}
            <button className="btn btn-secondary" onClick={refetch} disabled={loading}>
              {loading ? '⟳ Refreshing...' : '⟳ Refresh'}
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            {loading ? (
              <div className="loading"><div className="spinner"></div></div>
            ) : !positions?.length ? (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <p>No positions found</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Status</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Stop Loss</th>
                    <th>Target</th>
                    <th>Unrealized P&L</th>
                    <th>Realized P&L</th>
                    <th>R Multiple</th>
                    <th>Days Held</th>
                    <th>Entry Time</th>
                    <th>Exit Time</th>
                    <th>Strategy</th>
                    <th>Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.id}>
                      <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                      <td><span className={`badge ${getBadgeClass(pos.status)}`}>{pos.status}</span></td>
                      <td>{pos.quantity}</td>
                      <td>{formatCurrency(pos.entry_price)}</td>
                      <td>{pos.current_price ? formatCurrency(pos.current_price) : '-'}</td>
                      <td>{formatCurrency(pos.stop_loss)}</td>
                      <td>{formatCurrency(pos.target_price)}</td>
                      <td className={getPnlClass(pos.unrealized_pnl)}>
                        {pos.unrealized_pnl !== null ? formatCurrency(pos.unrealized_pnl) : '-'}
                      </td>
                      <td className={getPnlClass(pos.realized_pnl)}>
                        {pos.realized_pnl !== null ? formatCurrency(pos.realized_pnl) : '-'}
                      </td>
                      <td className={`r-multiple ${pos.r_multiple ? getPnlClass(pos.r_multiple) : ''}`}>
                        {pos.r_multiple !== null ? formatRMultiple(pos.r_multiple) : '-'}
                      </td>
                      <td>{pos.holding_days || '-'}</td>
                      <td>{formatDateTime(pos.entry_timestamp)}</td>
                      <td>{pos.exit_timestamp ? formatDateTime(pos.exit_timestamp) : '-'}</td>
                      <td style={{ fontSize: 12 }}>{pos.strategy_name}</td>
                      <td><span className={`badge ${pos.paper_or_live === 'DRY_RUN' ? 'badge-pending' : 'badge-buy'}`}>{pos.paper_or_live}</span></td>
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