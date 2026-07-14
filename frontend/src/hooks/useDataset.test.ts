/**
 * src/hooks/useDataset.test.ts
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { useDataset } from './useDataset';
import { makeDatasetInfo, makeValidationReport } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

describe('useDataset', () => {
  it('auto-fetches info on mount', async () => {
    const info = makeDatasetInfo();
    mock.onGet('/dataset/info').reply(200, { success: true, data: info, message: '' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.info?.total_images).toBe(3118);
  });

  it('sets info to null on 404 without setting error', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: 'No dataset_info.json' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.info).toBeNull();
    expect(result.current.error).toBeNull(); // 404 is expected
  });

  it('validate returns report on success', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    const report = makeValidationReport(true);
    mock.onPost('/dataset/validate').reply(200, { success: true, data: report, message: '' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    let res: typeof result.current.validation;
    await act(async () => { res = await result.current.validate(); });
    expect(res?.is_valid).toBe(true);
    expect(result.current.validation?.classes_found).toHaveLength(4);
  });

  it('prepare updates info on success', async () => {
    const info = makeDatasetInfo();
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    mock.onPost('/dataset/prepare').reply(200, { success: true, data: info, message: 'Done' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.prepare(); });
    expect(result.current.info?.total_images).toBe(3118);
  });

  it('prepare sets error on 422', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    mock.onPost('/dataset/prepare').reply(422, { detail: 'Bad ratios' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.prepare({ train_ratio: 0.9, val_ratio: 0.9, test_ratio: 0.9 }); });
    expect(result.current.error?.status).toBe(422);
  });

  it('refresh reloads info', async () => {
    const info = makeDatasetInfo();
    mock.onGet('/dataset/info').reply(200, { success: true, data: info, message: '' });
    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.refresh(); });
    expect(result.current.info).not.toBeNull();
  });
});
