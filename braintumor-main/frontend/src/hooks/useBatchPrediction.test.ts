/**
 * src/hooks/useBatchPrediction.test.ts
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { useBatchPrediction } from './useBatchPrediction';
import { makeBatchResult, makeFile, makeZipFile } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const wrap = <T>(data: T) => ({ success: true, data });

describe('useBatchPrediction', () => {
  it('initialises with null result', () => {
    const { result } = renderHook(() => useBatchPrediction());
    expect(result.current.result).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('runBatch sets result on success', async () => {
    const batch = makeBatchResult();
    mock.onPost('/predict/batch').reply(200, wrap(batch));
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => {
      await result.current.runBatch([makeFile(), makeFile('b.png', 'image/png')]);
    });
    expect(result.current.result?.total).toBe(3);
    expect(result.current.error).toBeNull();
  });

  it('runBatch sets error on failure', async () => {
    mock.onPost('/predict/batch').reply(400, { detail: 'No images' });
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => { await result.current.runBatch([]); });
    expect(result.current.error?.detail).toBe('No images');
    expect(result.current.result).toBeNull();
  });

  it('runZip sets result on success', async () => {
    const batch = makeBatchResult({ source_type: 'zip' });
    mock.onPost('/predict/zip').reply(200, wrap(batch));
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => { await result.current.runZip(makeZipFile()); });
    expect(result.current.result?.source_type).toBe('zip');
  });

  it('runZip sets error on 422', async () => {
    mock.onPost('/predict/zip').reply(422, { detail: 'Not a valid ZIP' });
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => { await result.current.runZip(makeZipFile()); });
    expect(result.current.error?.status).toBe(422);
  });

  it('reset clears result and error', async () => {
    const batch = makeBatchResult();
    mock.onPost('/predict/batch').reply(200, wrap(batch));
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => { await result.current.runBatch([makeFile()]); });
    act(() => { result.current.reset(); });
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('loading is false after completion', async () => {
    mock.onPost('/predict/batch').reply(200, wrap(makeBatchResult()));
    const { result } = renderHook(() => useBatchPrediction());
    await act(async () => { await result.current.runBatch([makeFile()]); });
    expect(result.current.loading).toBe(false);
  });
});
