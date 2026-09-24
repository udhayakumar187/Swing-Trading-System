import { useState, useEffect, useCallback } from 'react';

export function useApi(apiCall, deps = [], immediate = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(...args);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, deps);

  const refetch = useCallback(() => execute(), [execute]);

  return { data, loading, error, execute, refetch };
}

export function usePolling(apiCall, interval = 30000, deps = []) {
  const { data, loading, error, refetch } = useApi(apiCall, deps);

  useEffect(() => {
    if (interval <= 0) return;
    const timer = setInterval(() => {
      refetch();
    }, interval);
    return () => clearInterval(timer);
  }, [interval, refetch]);

  return { data, loading, error, refetch };
}