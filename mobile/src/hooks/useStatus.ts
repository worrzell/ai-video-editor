import { useCallback, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';

export interface StatusData {
  clips: string[];
  output_exists: boolean;
  download_url: string | null;
  authenticated: boolean;
  user: { username: string } | null;
  database: string;
  model: string;
}

export function useStatus(intervalMs = 8000) {
  const [data, setData] = useState<StatusData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await apiRequest<StatusData>('/api/status');
      setData(res);
      setError(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { data, error, loading, refresh };
}
