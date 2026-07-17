/**
 * src/hooks/usePreprocessing.test.ts
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { usePreprocessing } from './usePreprocessing';
import { makeQualityReport, makePreviewResult, makeFile } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

describe('usePreprocessing', () => {
  it('initialises with null report', () => {
    const { result } = renderHook(() => usePreprocessing());
    expect(result.current.report).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('checkQuality sets report on success', async () => {
    const report = makeQualityReport(true);
    mock.onPost('/preprocess/quality-check').reply(200, { success: true, data: report, message: 'OK' });
    const { result } = renderHook(() => usePreprocessing());
    await act(async () => { await result.current.checkQuality(makeFile()); });
    expect(result.current.report?.is_valid).toBe(true);
    expect(result.current.report?.checks).toHaveLength(6);
  });

  it('checkQuality sets error on 400', async () => {
    mock.onPost('/preprocess/quality-check').reply(400, { detail: 'Invalid image' });
    const { result } = renderHook(() => usePreprocessing());
    await act(async () => { await result.current.checkQuality(makeFile()); });
    expect(result.current.error?.status).toBe(400);
  });

  it('preview sets previewData on success', async () => {
    const prev = makePreviewResult();
    mock.onPost('/preprocess/preview').reply(200, { success: true, data: prev, message: 'OK' });
    const { result } = renderHook(() => usePreprocessing());
    await act(async () => { await result.current.preview(makeFile()); });
    expect(result.current.previewData?.augmented_b64).toHaveLength(2);
    expect(result.current.report?.is_valid).toBe(true); // updated from preview
  });

  it('reset clears all state', async () => {
    const prev = makePreviewResult();
    mock.onPost('/preprocess/preview').reply(200, { success: true, data: prev, message: 'OK' });
    const { result } = renderHook(() => usePreprocessing());
    await act(async () => { await result.current.preview(makeFile()); });
    act(() => { result.current.reset(); });
    expect(result.current.report).toBeNull();
    expect(result.current.previewData).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
