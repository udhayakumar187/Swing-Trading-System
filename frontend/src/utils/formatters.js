export function formatCurrency(value, currency = '₹') {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value).replace('₹', currency);
}

export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value, decimals = 2) {
  if (value === null || value === undefined) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

export function formatDate(dateString) {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateTime(dateString) {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function formatTime(dateString) {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function formatRMultiple(value) {
  if (value === null || value === undefined) return '-';
  const formatted = value.toFixed(2);
  return `${value >= 0 ? '+' : ''}${formatted}R`;
}

export function getPnlClass(value) {
  if (value === null || value === undefined) return '';
  return value >= 0 ? 'pnl-positive' : 'pnl-negative';
}

export function getBadgeClass(status) {
  const statusMap = {
    'OPEN': 'badge-open',
    'CLOSED': 'badge-closed',
    'STOPPED_OUT': 'badge-stopped',
    'TARGET_HIT': 'badge-target',
    'MANUALLY_CLOSED': 'badge-closed',
    'PENDING': 'badge-pending',
    'ACCEPTED': 'badge-pending',
    'REJECTED': 'badge-rejected',
    'EXECUTED': 'badge-filled',
    'EXPIRED': 'badge-closed',
    'COMPLETE': 'badge-complete',
    'FILLED': 'badge-filled',
    'PARTIAL': 'badge-pending',
    'BUY': 'badge-buy',
    'SELL': 'badge-sell',
  };
  return statusMap[status] || 'badge-pending';
}

export function truncate(text, length = 30) {
  if (!text) return '';
  return text.length > length ? text.slice(0, length) + '...' : text;
}