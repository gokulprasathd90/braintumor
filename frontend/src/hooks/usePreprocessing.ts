/**
 * src/hooks/usePreprocessing.ts — Quality check and preprocessing preview.
 *
 * Usage:
 *   const { checkQuality, preview, report, previewData, loading, error, reset } = usePreprocessing();
 */

import { useCallback, useState } from 'react';
import {
  qualityCheck,
  preprocessPreview,
  type PreviewOptions,
  type QualityCheckOptions,
} from '@/api/preprocessing';
import type { ApiError, PreprocessPreviewResult, QualityReport } from '@/types';

export interface UsePreprocessingReturn {
  checkQuality: (file: File, opts?: QualityCheckOptions) => Promise<QualityReport | null>;
  preview: (file: File, opts?: PreviewOptions) => Promise<PreprocessPreviewResult | null>;
  report: QualityReport | null;
  previewData: PreprocessPreviewResult | null;
  loading: boolean;
  error: ApiError | null;
  reset: () => void;
}

export function usePreprocessing(): UsePreprocessingReturn {
  const [report, setReport] = useState<QualityReport | null>(null);
  const [previewData, setPreviewData] = useState<PreprocessPreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const checkQuality = useCallback(
    async (file: File, opts: QualityCheckOptions = {}): Promise<QualityReport | null> => {
      setLoading(true);
      setError(null);
      try {
        const res = await qualityCheck(file, opts);
        setReport(res.data);
        return res.data;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const preview = useCallback(
    async (file: File, opts: PreviewOptions = {}): Promise<PreprocessPreviewResult | null> => {
      setLoading(true);
      setError(null);
      try {
        const res = await preprocessPreview(file, opts);
        setPreviewData(res.data);
        // Also update quality report from the same response
        if (res.data.quality) setReport(res.data.quality);
        return res.data;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setReport(null);
    setPreviewData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { checkQuality, preview, report, previewData, loading, error, reset };
}
