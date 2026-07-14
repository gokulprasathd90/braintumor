/**
 * src/hooks/useDataset.ts — Dataset info, validation, and preparation.
 *
 * Usage:
 *   const { info, validate, prepare, loading, error, refresh } = useDataset();
 */

import { useCallback, useEffect, useState } from 'react';
import {
  getDatasetInfo,
  validateDataset,
  prepareDataset,
} from '@/api/dataset';
import type {
  ApiError,
  DatasetInfo,
  DatasetPrepareRequest,
  DatasetValidationReport,
} from '@/types';

export interface UseDatasetReturn {
  info: DatasetInfo | null;
  validation: DatasetValidationReport | null;
  loading: boolean;
  validating: boolean;
  preparing: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
  validate: (rawDir?: string) => Promise<DatasetValidationReport | null>;
  prepare: (req?: Partial<DatasetPrepareRequest>) => Promise<DatasetInfo | null>;
}

export function useDataset(): UseDatasetReturn {
  const [info, setInfo] = useState<DatasetInfo | null>(null);
  const [validation, setValidation] = useState<DatasetValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDatasetInfo();
      setInfo(data);
    } catch (err) {
      // 404 is expected when dataset hasn't been prepared yet — not an error
      const apiErr = err as ApiError;
      if (apiErr.status !== 404) setError(apiErr);
      setInfo(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const validate = useCallback(
    async (rawDir?: string): Promise<DatasetValidationReport | null> => {
      setValidating(true);
      setError(null);
      try {
        const report = await validateDataset(rawDir);
        setValidation(report);
        return report;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setValidating(false);
      }
    },
    [],
  );

  const prepare = useCallback(
    async (req?: Partial<DatasetPrepareRequest>): Promise<DatasetInfo | null> => {
      setPreparing(true);
      setError(null);
      try {
        const { data } = await prepareDataset(req);
        setInfo(data);
        return data;
      } catch (err) {
        setError(err as ApiError);
        return null;
      } finally {
        setPreparing(false);
      }
    },
    [],
  );

  return {
    info,
    validation,
    loading,
    validating,
    preparing,
    error,
    refresh,
    validate,
    prepare,
  };
}
