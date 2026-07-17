/**
 * src/api/training.test.ts — training API module tests.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from './client';
import { startTraining, getTrainingStatus, listExperiments, getExperiment } from './training';
import { makeTrainingJob, makeCompletedJob, makeExperiment } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const REQ = {
  architecture: 'efficientnet' as const,
  epochs: 10,
  batch_size: 32,
  learning_rate: 0.0001,
  fine_tune: true,
  fine_tune_layers: 20,
  fine_tune_epochs: 5,
  seed: 42,
};

describe('startTraining', () => {
  it('returns job_id and experiment_id on 202', async () => {
    mock.onPost('/train/start').reply(202, {
      success: true,
      message: 'queued',
      job_id: 'j1',
      experiment_id: 'exp-001',
    });
    const res = await startTraining(REQ);
    expect(res.job_id).toBe('j1');
    expect(res.experiment_id).toBe('exp-001');
  });

  it('rejects on 422 for invalid config', async () => {
    mock.onPost('/train/start').reply(422, { detail: 'Invalid architecture' });
    await expect(startTraining({ ...REQ, architecture: 'bad' as never })).rejects.toMatchObject({ status: 422 });
  });
});

describe('getTrainingStatus', () => {
  it('returns TrainingJob on 200', async () => {
    const job = makeTrainingJob();
    mock.onGet('/train/status/job-abc-123').reply(200, { success: true, data: job });
    const res = await getTrainingStatus('job-abc-123');
    expect(res.job_id).toBe('job-abc-123');
    expect(res.status).toBe('running');
  });

  it('returns completed job with result', async () => {
    const job = makeCompletedJob();
    mock.onGet('/train/status/job-done').reply(200, { success: true, data: job });
    const res = await getTrainingStatus('job-done');
    expect(res.status).toBe('completed');
    expect((res.result as Record<string, number>)?.final_val_accuracy).toBeCloseTo(0.973);
  });

  it('rejects on 404 for unknown job', async () => {
    mock.onGet('/train/status/bad').reply(404, { detail: 'Job not found' });
    await expect(getTrainingStatus('bad')).rejects.toMatchObject({ status: 404 });
  });
});

describe('listExperiments', () => {
  it('returns array of experiments on 200', async () => {
    const exps = [makeExperiment(), makeExperiment({ architecture: 'resnet50' })];
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: exps, total: 2 });
    const res = await listExperiments();
    expect(res).toHaveLength(2);
    expect(res[0].architecture).toBe('efficientnet');
  });

  it('passes architecture filter as query param', async () => {
    mock.onGet('/train/experiments?architecture=resnet50').reply(200, { success: true, data: [], total: 0 });
    const res = await listExperiments({ architecture: 'resnet50' });
    expect(res).toHaveLength(0);
  });

  it('passes status filter as exp_status query param', async () => {
    mock.onGet('/train/experiments?exp_status=completed').reply(200, { success: true, data: [], total: 0 });
    const res = await listExperiments({ status: 'completed' });
    expect(Array.isArray(res)).toBe(true);
  });
});

describe('getExperiment', () => {
  it('returns full Experiment on 200', async () => {
    const exp = makeExperiment();
    mock.onGet('/train/experiments/exp-001').reply(200, { success: true, data: exp });
    const res = await getExperiment('exp-001');
    expect(res.experiment_id).toBe(exp.experiment_id);
    expect(res.best_val_accuracy).toBeCloseTo(0.973);
  });

  it('rejects on 404', async () => {
    mock.onGet('/train/experiments/missing').reply(404, { detail: 'Experiment not found' });
    await expect(getExperiment('missing')).rejects.toMatchObject({ status: 404 });
  });
});
