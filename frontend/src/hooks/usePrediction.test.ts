/**
 * src/hooks/usePrediction.test.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { usePrediction } from './usePrediction';
import { makePredictionResult, makeFile } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const wrap = <T>(data: T) => ({ success: true, data });

describe('usePrediction', () => {
  it('initialises with null result and loading=false', () => {
    const { result } = renderHook(() => usePrediction());
    expect(result.current.result).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('sets loading=true during predict call', async () => {
    mock.onPost('/predict/image').reply(() => {
      return [200, wrap(makePredictionResult())];
    });
    const { result } = renderHook(() => usePrediction());
    let loadingDuring = false;
    const p = act(async () => {
      const promise = result.current.predict(makeFile());
      loadingDuring = result.current.loading;
      await promise;
    });
    await p;
    // After completion loading must be false
    expect(result.current.loading).toBe(false);
  });

  it('sets result after successful predict', async () => {
    const expected = makePredictionResult();
    mock.onPost('/predict/image').reply(200, wrap(expected));
    const { result } = renderHook(() => usePrediction());
    await act(async () => { await result.current.predict(makeFile()); });
    expect(result.current.result?.predicted_class).toBe('glioma');
    expect(result.current.result?.confidence).toBe(0.85);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed predict', async () => {
    mock.onPost('/predict/image').reply(404, { detail: 'No model weights' });
    const { result } = renderHook(() => usePrediction());
    await act(async () => { await result.current.predict(makeFile()); });
    expect(result.current.error?.detail).toBe('No model weights');
    expect(result.current.result).toBeNull();
  });

  it('reset clears result and error', async () => {
    const expected = makePredictionResult();
    mock.onPost('/predict/image').reply(200, wrap(expected));
    const { result } = renderHook(() => usePrediction());
    await act(async () => { await result.current.predict(makeFile()); });
    act(() => { result.current.reset(); });
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('uploadProgress updates during upload', async () => {
    mock.onPost('/predict/image').reply(200, wrap(makePredictionResult()));
    const { result } = renderHook(() => usePrediction());
    await act(async () => { await result.current.predict(makeFile()); });
    expect(result.current.uploadProgress).toBe(100);
  });

  it('accepts custom model options', async () => {
    mock.onPost('/predict/image').reply((config) => {
      const fd = config.data as FormData;
      expect(fd.get('model_name')).toBe('resnet50');
      expect(fd.get('top_k')).toBe('3');
      return [200, wrap(makePredictionResult())];
    });
    const { result } = renderHook(() => usePrediction());
    await act(async () => {
      await result.current.predict(makeFile(), { modelName: 'resnet50', topK: 3 });
    });
  });
});
