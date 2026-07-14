/**
 * src/hooks/useTraining.ts — Training job management with real-time polling.
 *
 * Usage:
 *   const { start, status, job, loading, error, stopPolling } = useTraining();
 *   await start({ architecture: 'efficientnet', epochs: 30, ... });
 *   // Polling starts automatically once a job is running.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  startTraining,
  getTrainingStatus,
  type TrainStartResponse,
} from '@/api/training';
import type { ApiError, TrainingJob, TrainingStartRequest } from '@/types';

const POLL_INTERVAL_MS = Number(
  import.meta.env.VITE_TRAINING_POLL_INTERVAL_MS ?? 3_000,
);

export interface UseTrainingReturn {
  start: (req: TrainingStartRequest) => Promise<TrainStartResponse | null>;
  job: TrainingJob | null;
  loading: boolean;        // true while the start call is in flight
  polling: boolean;        // true while actively polling
  error: ApiError | null;
  stopPolling: () => void;
  reset: () => void;
}

export function useTraining(): UseTrainingReturn {
  const [job, setJob] = useState<TrainingJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setPolling(false);
  }, []);

  // ── Poll for status ───────────────────────────────────────────────────────
  const startPolling = useCallback(
    (jobId: string) => {
      if (pollingRef.current !== null) clearInterval(pollingRef.current);
      setPolling(true);

      pollingRef.current = setInterval(async () => {
        try {
          const updated = await getTrainingStatus(jobId);
          setJob(updated);

          // Stop once terminal state is reached
          if (
            updated.status === 'completed' ||
            updated.status === 'failed' ||
            updated.status === 'interrupted'
          ) {
            stopPolling();
          }
        } catch (err) {
          setError(err as ApiError);
          stopPolling();
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  // Clean up on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  // ── Start training job ────────────────────────────────────────────────────
  const start = useCallback(
    async (req: TrainingStartRequest): Promise<TrainStartResponse | null> => {
      setLoading(true);
      setError(null);

      try {
        const res = await startTraining(req);
        const stub: TrainingJob = {
          job_id: res.job_id,
          status: 'queued',
          experiment_id: res.experiment_id,
          created_at: new Date().toISOString(),
          started_at: null,
          finished_at: null,
          result: null,
          error: null,
        };
        setJob(stub);
        jobIdRef.current = res.job_id;
        startPolling(res.job_id);
        return res;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [startPolling],
  );

  const reset = useCallback(() => {
    stopPolling();
    setJob(null);
    setError(null);
    setLoading(false);
    jobIdRef.current = null;
  }, [stopPolling]);

  return { start, job, loading, polling, error, stopPolling, reset };
}
