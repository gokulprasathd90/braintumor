/**
 * src/api/dataset.test.ts — dataset API module tests.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from './client';
import { getDatasetInfo, validateDataset, prepareDataset } from './dataset';
import { makeDatasetInfo, makeValidationReport } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

describe('getDatasetInfo', () => {
  it('returns DatasetInfo on 200', async () => {
    const info = makeDatasetInfo();
    mock.onGet('/dataset/info').reply(200, { success: true, data: info, message: 'OK' });
    const res = await getDatasetInfo();
    expect(res.total_images).toBe(3118);
    expect(res.classes).toHaveLength(4);
  });

  it('rejects on 404 when dataset not prepared', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: 'No dataset_info.json found' });
    await expect(getDatasetInfo()).rejects.toMatchObject({ status: 404 });
  });

  it('passes processedDir as query param', async () => {
    const info = makeDatasetInfo();
    mock.onGet('/dataset/info?processed_dir=%2Fcustom%2Fpath').reply(200, { success: true, data: info, message: 'OK' });
    const res = await getDatasetInfo('/custom/path');
    expect(res.total_images).toBe(3118);
  });
});

describe('validateDataset', () => {
  it('returns valid report on 200', async () => {
    const report = makeValidationReport(true);
    mock.onPost('/dataset/validate').reply(200, { success: true, data: report, message: 'Valid' });
    const res = await validateDataset();
    expect(res.is_valid).toBe(true);
    expect(res.classes_found).toHaveLength(4);
  });

  it('returns invalid report with errors on 200', async () => {
    const report = makeValidationReport(false);
    mock.onPost('/dataset/validate').reply(200, { success: false, data: report, message: 'Errors' });
    const res = await validateDataset();
    expect(res.is_valid).toBe(false);
    expect(res.errors.length).toBeGreaterThan(0);
  });
});

describe('prepareDataset', () => {
  it('returns DatasetInfo on 200', async () => {
    const info = makeDatasetInfo();
    mock.onPost('/dataset/prepare').reply(200, { success: true, data: info, message: 'Done' });
    const res = await prepareDataset();
    expect(res.data.total_images).toBe(3118);
    expect(res.message).toBe('Done');
  });

  it('uses default ratios when not provided', async () => {
    const info = makeDatasetInfo();
    mock.onPost('/dataset/prepare').reply((config) => {
      const body = JSON.parse(config.data as string);
      expect(body.train_ratio).toBe(0.7);
      expect(body.val_ratio).toBe(0.15);
      return [200, { success: true, data: info, message: 'OK' }];
    });
    await prepareDataset();
  });

  it('rejects on 422 for invalid ratios', async () => {
    mock.onPost('/dataset/prepare').reply(422, { detail: 'Ratios must sum to 1.0' });
    await expect(prepareDataset({ train_ratio: 0.5, val_ratio: 0.5, test_ratio: 0.5 })).rejects.toMatchObject({ status: 422 });
  });
});
