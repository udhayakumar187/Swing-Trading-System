import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { signalsApi } from '../services/api';
import { formatCurrency, formatDateTime, getBadgeClass } from '../utils/formatters';

export default function SignalsPage() {
  const [decisionFilter, setDecisionFilter] = useState('');
  
  const { data: signals, loading, refetch } = useApi(
    () => signalsApi.getAll(1, decisionFilter || undefined), 
    [decisionFilter], 
    true
  );

  const decisionOptions = ['', 'PENDING', 'ACCEPTED', 'REJECTED', 'EXECUTED', 'EXPIRED'];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Signals</h1>
        <p className="page-subtitle">Generated trading signals with decisions</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14, color: '#6b7280' }}>Filter:</span>
            {decisionOptions.map((decision) => (
              <button
                key={decision}
                className={`btn ${decisionFilter === decision ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: 13 }}
                onClick={() => setDecisionFilter(decision)}
              >
                {decision || 'All'}
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
            ) : !signals?.length ? (
              <div className="empty-state">
                <div className="empty-state-icon">📊</div>
                <p>No signals generated yet</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Signal Time</th>
                    <th>Entry</th>
                    <th>Stop Loss</th>
                    <th>Target</th>
                    <th>Risk ₹</th>
                    <th>R:R</th>
                    <th>Decision</th>
                    <th>Reason</th>
                    <th>Strategy</th>
                    <th>Run ID</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((signal) => (
                    <tr key={signal.id}>
                      <td style={{ fontWeight: 600 }}>{signal.symbol}</td>
                      <td><span className={`badge ${signal.signal_type === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>{signal.signal_type}</span></td>
                      <td>{formatDateTime(signal.signal_timestamp)}</td>
                      <td>{formatCurrency(signal.entry_price)}</td>
                      <td>{formatCurrency(signal.stop_loss)}</td>
                      <td>{formatCurrency(signal.target_price)}</td>
                      <td>{formatCurrency(signal.risk_amount)}</td>
                      <td>{signal.risk_reward_ratio?.toFixed(1)}R</td>
                      <td><span className={`badge ${getBadgeClass(signal.decision)}`}>{signal.decision}</span></td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12 }}>
                        {signal.reason || '-'}
                      </td>
                      <td style={{ fontSize: 12 }}>{signal.strategy_name}</td>
                      <td>{signal.trading_run_id || '-'}</td>
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