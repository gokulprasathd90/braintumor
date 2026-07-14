/**
 * src/hooks/useTraining.test.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { useTraining } from './useTraining';
import { makeTrainingJob, makeCompletedJob } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => { mock.reset(); vi.useFakeTimers(); });
afterEach(() => { mock.reset(); vi.useRealTimers(); });

const REQ = {
  architecture: 'efficientnet' as const,
  epochs: 10, batch_size: 32, learning_rate: 0.0001,
  fine_tune: true, fine_tune_layers: 20, fine_tune_epochs: 5, seed: 42,
};

describe('useTraining', () => {
  it('initialises with null job', () => {
    const { result } = renderHook(() => useTraining());
    expect(result.current.job).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.polling).toBe(false);
  });

  it('start sets job stub with queued status', async () => {
    mock.onPost('/train/start').reply(202, { success: true, message: '', job_id: 'j1', experiment_id: 'exp-1' });
    mock.onGet('/train/status/j1').reply(200, { success: true, data: makeTrainingJob({ job_id: 'j1' }) });
    const { result } = renderHook(() => useTraining());
    await act(async () => { await result.current.start(REQ); });
    expect(result.current.job?.job_id).toBe('j1');
    expect(result.current.polling).toBe(true);
  });

  it('polling stops on completed status', async () => {
    mock.onPost('/train/start').reply(202, { success: true, message: '', job_id: 'j2', experiment_id: 'exp-2' });
    mock.onGet('/train/status/j2').reply(200, { success: true, data: makeCompletedJob() });
    const { result } = renderHook(() => useTraining());
    await act(async () => { await result.current.start(REQ); });
    // Advance timers to trigger one poll
    await act(async () => { vi.advanceTimersByTime(3500); });
    expect(result.current.job?.status).toBe('completed');
    expect(result.current.polling).toBe(false);
  });

  it('sets error when start fails', async () => {
    mock.onPost('/train/start').reply(422, { detail: 'Bad config' });
    const { result } = renderHook(() => useTraining());
    await act(async () => { await result.current.start(REQ); });
    expect(result.current.error?.detail).toBe('Bad config');
    expect(result.current.job).toBeNull();
  });

  it('stopPolling sets polling=false', async () => {
    mock.onPost('/train/start').reply(202, { success: true, message: '', job_id: 'j3', experiment_id: 'e3' });
    mock.onGet('/train/status/j3').reply(200, { success: true, data: makeTrainingJob({ job_id: 'j3' }) });
    const { result } = renderHook(() => useTraining());
    await act(async () => { await result.current.start(REQ); });
    act(() => { result.current.stopPolling(); });
    expect(result.current.polling).toBe(false);
  });

  it('reset clears job and error', async () => {
    mock.onPost('/train/start').reply(422, { detail: 'Oops' });
    const { result } = renderHook(() => useTraining());
    await act(async () => { await result.current.start(REQ); });
    act(() => { result.current.reset(); });
    expect(result.current.job).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
