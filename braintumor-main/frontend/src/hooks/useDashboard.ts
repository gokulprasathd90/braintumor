/**
 * src/hooks/useDashboard.ts — Live-polling hook for dashboard metrics.
 *
 * Usage:
 *   const { overview, system, inference, training, loading, error, refresh } =
 *     useDashboard({ pollInterval: 5000 });
 *
 * Polling starts immediately on mount and stops on unmount.
 * Manual refresh is available via the returned `refresh()` function.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getDashboardOverview,
  getSystemMetrics,
  getInferenceMetrics,
  getTrainingMetrics,
} from '@/api/dashboard';
import type {
  DashboardOverview,
  SystemMetrics,
  InferenceMetrics,
  TrainingMetrics,
} from '@/types';

const DEFAULT_POLL_INTERVAL_MS = Number(
  import.meta.env.VITE_DASHBOARD_POLL_INTERVAL_MS ?? 5_000,
);

export interface UseDashboardOptions {
  /** Polling interval in ms. Set to 0 to disable auto-refresh. */
  pollInterval?: number;
  /** Which metric domains to load. Defaults to all. */
  domains?: Array<'overview' | 'system' | 'inference' | 'training'>;
}

export interface UseDashboardReturn {
  overview: DashboardOverview | null;
  system: SystemMetrics | null;
  inference: InferenceMetrics | null;
  training: TrainingMetrics | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => void;
}

export function useDashboard(opts: UseDashboardOptions = {}): UseDashboardReturn {
  const {
    pollInterval = DEFAULT_POLL_INTERVAL_MS,
    domains = ['overview', 'system', 'inference', 'training'],
  } = opts;

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [system, setSystem] = useState<SystemMetrics | null>(null);
  const [inference, setInference] = useState<InferenceMetrics | null>(null);
  const [training, setTraining] = useState<TrainingMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchAll = useCallback(async () => {
    try {
      const promises: Promise<void>[] = [];

      if (domains.includes('overview')) {
        promises.push(
          getDashboardOverview()
            .then((d) => { if (mountedRef.current) setOverview(d); })
            .catch(() => {}),
        );
      }
      if (domains.includes('system')) {
        promises.push(
          getSystemMetrics()
            .then((d) => { if (mountedRef.current) setSystem(d); })
            .catch(() => {}),
        );
      }
      if (domains.includes('inference')) {
        promises.push(
          getInferenceMetrics()
            .then((d) => { if (mountedRef.current) setInference(d); })
            .catch(() => {}),
        );
      }
      if (domains.includes('training')) {
        promises.push(
          getTrainingMetrics()
            .then((d) => { if (mountedRef.current) setTraining(d); })
            .catch(() => {}),
        );
      }

      await Promise.all(promises);

      if (mountedRef.current) {
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard metrics');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [domains]); // eslint-disable-line react-hooks/exhaustive-deps

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    mountedRef.current = true;

    // Initial fetch
    fetchAll();

    // Start polling if interval > 0
    if (pollInterval > 0) {
      timerRef.current = setInterval(fetchAll, pollInterval);
    }

    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [fetchAll, pollInterval, stopPolling]);

  return { overview, system, inference, training, loading, error, lastUpdated, refresh };
}

// ── Focused single-domain hook ────────────────────────────────────────────

export function useSystemMetrics(pollInterval = DEFAULT_POLL_INTERVAL_MS) {
  const { system, loading, error, lastUpdated, refresh } = useDashboard({
    pollInterval,
    domains: ['system'],
  });
  return { data: system, loading, error, lastUpdated, refresh };
}

export function useInferenceMetrics(pollInterval = DEFAULT_POLL_INTERVAL_MS) {
  const { inference, loading, error, lastUpdated, refresh } = useDashboard({
    pollInterval,
    domains: ['inference'],
  });
  return { data: inference, loading, error, lastUpdated, refresh };
}

export function useTrainingMetrics(pollInterval = DEFAULT_POLL_INTERVAL_MS) {
  const { training, loading, error, lastUpdated, refresh } = useDashboard({
    pollInterval,
    domains: ['training'],
  });
  return { data: training, loading, error, lastUpdated, refresh };
}
