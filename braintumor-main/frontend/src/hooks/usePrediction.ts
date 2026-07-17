/**
 * src/hooks/usePrediction.ts — Single-image inference hook.
 *
 * Usage:
 *   const { predict, result, loading, error, reset, uploadProgress } = usePrediction();
 *   await predict(file, { topK: 3, generateGradcam: true });
 */

import { useCallback, useRef, useState } from 'react';
import { predictImage, type PredictImageOptions } from '@/api/prediction';
import type { ApiError, PredictionResult } from '@/types';

export interface UsePredictionReturn {
  predict: (file: File, options?: PredictImageOptions) => Promise<void>;
  result: PredictionResult | null;
  loading: boolean;
  error: ApiError | null;
  uploadProgress: number;        // 0–100
  reset: () => void;
}

export function usePrediction(): UsePredictionReturn {
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Allow callers to abort in-flight requests
  const abortRef = useRef<AbortController | null>(null);

  const predict = useCallback(
    async (file: File, options: PredictImageOptions = {}) => {
      // Cancel any previous in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      setLoading(true);
      setError(null);
      setResult(null);
      setUploadProgress(0);

      try {
        const data = await predictImage(file, {
          ...options,
          onUploadProgress: (pct) => setUploadProgress(pct),
        });
        setResult(data);
        setUploadProgress(100);
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setResult(null);
    setError(null);
    setLoading(false);
    setUploadProgress(0);
  }, []);

  return { predict, result, loading, error, uploadProgress, reset };
}
