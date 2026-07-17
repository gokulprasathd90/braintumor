/**
 * src/hooks/useBatchPrediction.ts — Batch and ZIP inference hook.
 *
 * Usage:
 *   const { runBatch, runZip, result, loading, error, reset } = useBatchPrediction();
 *   await runBatch(files, { modelName: 'resnet50', topK: 2 });
 *   await runZip(zipFile);
 */

import { useCallback, useState } from 'react';
import { predictBatch, predictZip, type PredictBatchOptions } from '@/api/prediction';
import type { ApiError, BatchPredictionResult } from '@/types';

export interface UseBatchPredictionReturn {
  runBatch: (files: File[], options?: PredictBatchOptions) => Promise<void>;
  runZip: (archive: File, options?: PredictBatchOptions) => Promise<void>;
  result: BatchPredictionResult | null;
  loading: boolean;
  error: ApiError | null;
  reset: () => void;
}

export function useBatchPrediction(): UseBatchPredictionReturn {
  const [result, setResult] = useState<BatchPredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const runBatch = useCallback(
    async (files: File[], options: PredictBatchOptions = {}) => {
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await predictBatch(files, options);
        setResult(data);
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const runZip = useCallback(
    async (archive: File, options: PredictBatchOptions = {}) => {
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await predictZip(archive, options);
        setResult(data);
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLoading(false);
  }, []);

  return { runBatch, runZip, result, loading, error, reset };
}
