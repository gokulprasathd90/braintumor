/**
 * src/api/client.test.ts — Axios client: interceptors, retries, error parsing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient, get, post } from './client';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });

beforeEach(() => mock.reset());
afterEach(() => mock.reset());

describe('apiClient — base configuration', () => {
  it('has baseURL set to /api/v1', () => {
    expect(apiClient.defaults.baseURL).toBe('/api/v1');
  });

  it('GET /health returns data on 200', async () => {
    mock.onGet('/health').reply(200, { status: 'ok' });
    const res = await apiClient.get('/health');
    expect(res.data).toEqual({ status: 'ok' });
  });

  it('get() helper unwraps response data', async () => {
    mock.onGet('/test').reply(200, { value: 42 });
    const data = await get<{ value: number }>('/test');
    expect(data).toEqual({ value: 42 });
  });

  it('post() helper sends JSON body', async () => {
    mock.onPost('/train/start').reply(202, { job_id: 'abc' });
    const data = await post<{ job_id: string }>('/train/start', { architecture: 'cnn' });
    expect(data.job_id).toBe('abc');
  });
});

describe('apiClient — error handling', () => {
  it('rejects with ApiError containing detail from response', async () => {
    mock.onGet('/fail').reply(404, { detail: 'Not found' });
    await expect(get('/fail')).rejects.toMatchObject({ detail: 'Not found', status: 404 });
  });

  it('rejects with ApiError on 422 with detail string', async () => {
    mock.onPost('/bad').reply(422, { detail: 'Validation error' });
    await expect(post('/bad', {})).rejects.toMatchObject({ status: 422, detail: 'Validation error' });
  });

  it('rejects with ApiError on network error', async () => {
    mock.onGet('/net-error').networkError();
    await expect(get('/net-error')).rejects.toHaveProperty('detail');
  });

  it('exposes status 0 on network error', async () => {
    mock.onGet('/net-error').networkError();
    const err = await get('/net-error').catch((e) => e);
    expect(err.status).toBe(0);
  });

  it('falls back to err.message when no response body', async () => {
    mock.onGet('/timeout').timeout();
    const err = await get('/timeout').catch((e) => e);
    expect(typeof err.detail).toBe('string');
    expect(err.detail.length).toBeGreaterThan(0);
  });
});

describe('apiClient — automatic retry', () => {
  it('retries up to 2 times on 500 then rejects', async () => {
    let calls = 0;
    mock.onGet('/flaky').reply(() => { calls++; return [500, { detail: 'server error' }]; });
    await get('/flaky').catch(() => null);
    // 1 original + 2 retries = 3 total calls
    expect(calls).toBe(3);
  });

  it('succeeds on second attempt (transient 500)', async () => {
    let calls = 0;
    mock.onGet('/recover').reply(() => {
      calls++;
      return calls < 2 ? [500, {}] : [200, { ok: true }];
    });
    const data = await get<{ ok: boolean }>('/recover');
    expect(data.ok).toBe(true);
    expect(calls).toBe(2);
  });

  it('does NOT retry 4xx errors', async () => {
    let calls = 0;
    mock.onGet('/notfound').reply(() => { calls++; return [404, { detail: 'not found' }]; });
    await get('/notfound').catch(() => null);
    expect(calls).toBe(1);
  });
});
