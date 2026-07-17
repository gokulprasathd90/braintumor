/**
 * src/api/models.test.ts — models API module tests.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from './client';
import { listModels, getActiveModel, reloadModel } from './models';
import { makeModelList, makeCacheStats, makeActiveModel } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

describe('listModels', () => {
  it('returns models array and cache_stats on 200', async () => {
    mock.onGet('/models').reply(200, {
      success: true,
      data: makeModelList(),
      cache_stats: makeCacheStats(),
    });
    const { models, cache_stats } = await listModels();
    expect(models).toHaveLength(4);
    expect(models.map((m) => m.name)).toContain('efficientnet');
    expect(cache_stats.capacity).toBe(4);
  });

  it('each model entry has required keys', async () => {
    mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
    const { models } = await listModels();
    for (const m of models) {
      expect(m).toHaveProperty('name');
      expect(m).toHaveProperty('available');
      expect(m).toHaveProperty('cached');
    }
  });
});

describe('getActiveModel', () => {
  it('returns ActiveModelInfo on 200', async () => {
    mock.onGet('/models/active').reply(200, { success: true, data: makeActiveModel() });
    const res = await getActiveModel();
    expect(res.model_name).toBe('efficientnet');
    expect(res.available).toBe(true);
  });

  it('rejects on 404 when no weights exist', async () => {
    mock.onGet('/models/active').reply(404, { detail: 'No saved weights' });
    await expect(getActiveModel()).rejects.toMatchObject({ status: 404 });
  });
});

describe('reloadModel', () => {
  it('returns success response on 200', async () => {
    mock.onPost('/models/reload').reply(200, {
      success: true,
      message: "Model 'efficientnet' reloaded.",
      model_name: 'efficientnet',
    });
    const res = await reloadModel('efficientnet');
    expect(res.success).toBe(true);
    expect(res.model_name).toBe('efficientnet');
  });

  it('rejects on 404 when model not trained', async () => {
    mock.onPost('/models/reload').reply(404, { detail: 'No saved weights for cnn' });
    await expect(reloadModel('cnn')).rejects.toMatchObject({ status: 404 });
  });

  it('rejects on 422 for missing body', async () => {
    mock.onPost('/models/reload').reply(422, { detail: 'Field required' });
    await expect(reloadModel('')).rejects.toMatchObject({ status: 422 });
  });
});
