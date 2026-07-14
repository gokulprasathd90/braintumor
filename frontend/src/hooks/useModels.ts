/**
 * src/hooks/useModels.ts — Model list, active model, and hot-reload.
 *
 * Usage:
 *   const { models, cacheStats, activeModel, reload, loading, error, refresh } = useModels();
 */

import { useCallback, useEffect, useState } from 'react';
import { listModels, getActiveModel, reloadModel } from '@/api/models';
import type { ActiveModelInfo, ApiError, CacheStats, ModelInfo } from '@/types';

export interface UseModelsReturn {
  models: ModelInfo[];
  cacheStats: CacheStats | null;
  activeModel: ActiveModelInfo | null;
  reload: (modelName: string) => Promise<boolean>;
  loading: boolean;
  reloading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
}

export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [activeModel, setActiveModel] = useState<ActiveModelInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [listResult, active] = await Promise.allSettled([
        listModels(),
        getActiveModel(),
      ]);

      if (listResult.status === 'fulfilled') {
        setModels(listResult.value.models);
        setCacheStats(listResult.value.cache_stats);
      }
      if (active.status === 'fulfilled') {
        setActiveModel(active.value);
      }
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on mount
  useEffect(() => {
    refresh();
  }, [refresh]);

  const reload = useCallback(
    async (modelName: string): Promise<boolean> => {
      setReloading(true);
      setError(null);
      try {
        await reloadModel(modelName);
        await refresh();
        return true;
      } catch (err) {
        setError(err as ApiError);
        return false;
      } finally {
        setReloading(false);
      }
    },
    [refresh],
  );

  return {
    models,
    cacheStats,
    activeModel,
    reload,
    loading,
    reloading,
    error,
    refresh,
  };
}
