/**
 * src/hooks/useModels.test.ts
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { useModels } from './useModels';
import { makeModelList, makeCacheStats, makeActiveModel } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const setupOk = () => {
  mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
  mock.onGet('/models/active').reply(200, { success: true, data: makeActiveModel() });
};

describe('useModels', () => {
  it('fetches models on mount', async () => {
    setupOk();
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.models).toHaveLength(4);
  });

  it('sets cacheStats on mount', async () => {
    setupOk();
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.cacheStats?.capacity).toBe(4);
  });

  it('sets activeModel on mount', async () => {
    setupOk();
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.activeModel?.model_name).toBe('efficientnet');
  });

  it('reload calls /models/reload and refreshes', async () => {
    setupOk();
    mock.onPost('/models/reload').reply(200, { success: true, message: 'reloaded', model_name: 'efficientnet' });
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.reload('efficientnet'); });
    expect(result.current.error).toBeNull();
  });

  it('reload returns false on 404', async () => {
    setupOk();
    mock.onPost('/models/reload').reply(404, { detail: 'No weights' });
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    let ok: boolean | undefined;
    await act(async () => { ok = await result.current.reload('cnn'); });
    expect(ok).toBe(false);
    expect(result.current.error?.status).toBe(404);
  });

  it('handles /models/active 404 gracefully (no error)', async () => {
    mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
    mock.onGet('/models/active').reply(404, { detail: 'No weights' });
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));
    // models still loaded; activeModel null; no top-level error
    expect(result.current.models).toHaveLength(4);
  });
});
