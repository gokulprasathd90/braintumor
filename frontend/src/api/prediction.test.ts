/**
 * src/api/prediction.test.ts — prediction API module tests.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from './client';
import { predictImage, predictBatch, predictZip } from './prediction';
import { makePredictionResult, makeBatchResult, makeFile, makeZipFile } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const wrap = <T>(data: T) => ({ success: true, data });

describe('predictImage', () => {
  it('returns PredictionResult on 200', async () => {
    const result = makePredictionResult();
    mock.onPost('/predict/image').reply(200, wrap(result));
    const data = await predictImage(makeFile());
    expect(data.predicted_class).toBe('glioma');
    expect(data.confidence).toBe(0.85);
  });

  it('sends form data with model_name when provided', async () => {
    const result = makePredictionResult();
    mock.onPost('/predict/image').reply((config) => {
      expect(config.data).toBeInstanceOf(FormData);
      return [200, wrap(result)];
    });
    await predictImage(makeFile(), { modelName: 'resnet50' });
  });

  it('rejects with ApiError on 400', async () => {
    mock.onPost('/predict/image').reply(400, { detail: 'Unsupported file type' });
    await expect(predictImage(makeFile())).rejects.toMatchObject({ status: 400 });
  });

  it('rejects on 404 (no model weights)', async () => {
    mock.onPost('/predict/image').reply(404, { detail: 'Model not found' });
    await expect(predictImage(makeFile())).rejects.toMatchObject({ status: 404 });
  });
});

describe('predictBatch', () => {
  it('returns BatchPredictionResult on 200', async () => {
    const result = makeBatchResult();
    mock.onPost('/predict/batch').reply(200, wrap(result));
    const data = await predictBatch([makeFile(), makeFile('b.png', 'image/png')]);
    expect(data.total).toBe(3);
    expect(data.succeeded).toBe(2);
  });

  it('sends all files in FormData', async () => {
    const result = makeBatchResult();
    mock.onPost('/predict/batch').reply((config) => {
      expect(config.data).toBeInstanceOf(FormData);
      return [200, wrap(result)];
    });
    await predictBatch([makeFile(), makeFile('b.png', 'image/png')]);
  });

  it('rejects on 400', async () => {
    mock.onPost('/predict/batch').reply(400, { detail: 'No images' });
    await expect(predictBatch([])).rejects.toMatchObject({ status: 400 });
  });
});

describe('predictZip', () => {
  it('returns BatchPredictionResult on 200', async () => {
    const result = makeBatchResult({ source_type: 'zip' });
    mock.onPost('/predict/zip').reply(200, wrap(result));
    const data = await predictZip(makeZipFile());
    expect(data.source_type).toBe('zip');
  });

  it('appends model_name to form when provided', async () => {
    const result = makeBatchResult({ source_type: 'zip' });
    mock.onPost('/predict/zip').reply((config) => {
      expect(config.data).toBeInstanceOf(FormData);
      return [200, wrap(result)];
    });
    await predictZip(makeZipFile(), { modelName: 'resnet50' });
  });

  it('rejects on 422 for non-ZIP file', async () => {
    mock.onPost('/predict/zip').reply(422, { detail: 'Not a valid ZIP' });
    await expect(predictZip(makeZipFile())).rejects.toMatchObject({ status: 422 });
  });
});
