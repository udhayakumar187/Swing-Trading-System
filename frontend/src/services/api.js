import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const healthApi = {
  check: () => api.get('/health'),
  db: () => api.get('/health/db'),
};

export const portfolioApi = {
  getSummary: (accountId = 1) => api.get('/portfolio', { params: { account_id: accountId } }),
  getAccount: (accountId = 1) => api.get('/account', { params: { account_id: accountId } }),
};

export const positionsApi = {
  getAll: (accountId = 1, status) => api.get('/positions', { 
    params: { account_id: accountId, status } 
  }),
};

export const ordersApi = {
  getAll: (accountId = 1, status, limit = 100) => api.get('/orders', { 
    params: { account_id: accountId, status, limit } 
  }),
};

export const signalsApi = {
  getAll: (accountId = 1, decision, limit = 100) => api.get('/signals', { 
    params: { account_id: accountId, decision, limit } 
  }),
};

export const tradingRunsApi = {
  getAll: (accountId = 1, limit = 50) => api.get('/trading-runs', { 
    params: { account_id: accountId, limit } 
  }),
};

export const riskSettingsApi = {
  get: (accountId = 1) => api.get('/risk-settings', { params: { account_id: accountId } }),
  update: (data, accountId = 1) => api.post('/risk-settings', data, { params: { account_id: accountId } }),
};

export const tradingApi = {
  run: (accountId = 1) => api.post('/trading/run', null, { params: { account_id: accountId } }),
};

export const logsApi = {
  get: (accountId = 1, limit = 100) => api.get('/logs', { params: { account_id: accountId, limit } }),
};

export default api;