import React from 'react';
import { useApi } from '../hooks/useApi';
import { logsApi } from '../services/api';
import { formatDateTime, getBadgeClass } from '../utils/formatters';

export default function LogsPage() {
  const { data: logs, loading, refetch } = useApi(
    () => logsApi.get(1, 200), 
    [], 
    true
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Audit Logs</h1>
        <p className="page-subtitle">System events, risk rejections, and broker events</p>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            {loading ? (
              <div className="loading"><div className="spinner"></div></div>
            ) : !logs?.length ? (
              <div className="empty-state">
                <div className="empty-state-icon">📝</div>
                <p>No audit logs available</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Event Type</th>
                    <th>Event Code</th>
                    <th>Severity</th>
                    <th>Symbol</th>
                    <th>Message</th>
                    <th>Run ID</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} style={{ fontSize: 13 }}>
                      <td style={{ fontFamily: 'monospace', color: '#6b7280' }}>{formatDateTime(log.created_at)}</td>
                      <td>{log.event_type}</td>
                      <td><span className={`badge ${getBadgeClass(log.event_code)}`} style={{ textTransform: 'none', fontSize: 10 }}>{log.event_code}</span></td>
                      <td>
                        <span className={`badge ${log.severity === 'ERROR' ? 'badge-stopped' : log.severity === 'WARNING' ? 'badge-pending' : 'badge-complete'}`}>
                          {log.severity}
                        </span>
                      </td>
                      <td>{log.symbol || '-'}</td>
                      <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.message}</td>
                      <td>{log.trading_run_id || '-'}</td>
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