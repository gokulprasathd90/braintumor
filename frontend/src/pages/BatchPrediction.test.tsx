/**
 * src/pages/BatchPrediction.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import BatchPrediction from './BatchPrediction';
import { makeBatchResult, makeFile, makeModelList, makeCacheStats, makeActiveModel } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const setupModels = () => {
  mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
  mock.onGet('/models/active').reply(200, { success: true, data: makeActiveModel() });
};

const renderPage = () =>
  render(<MemoryRouter><BatchPrediction /></MemoryRouter>);

describe('BatchPrediction', () => {
  it('renders heading', () => {
    setupModels();
    renderPage();
    expect(screen.getByText('Batch Prediction')).toBeInTheDocument();
  });

  it('renders mode toggle buttons', async () => {
    setupModels();
    renderPage();
    // Mode buttons appear in the settings panel
    const buttons = screen.getAllByRole('button');
    const labels = buttons.map((b) => b.textContent ?? '');
    expect(labels.some((l) => /multiple files/i.test(l))).toBe(true);
    expect(labels.some((l) => /zip archive/i.test(l))).toBe(true);
  });

  it('switches to ZIP mode on button click', async () => {
    setupModels();
    renderPage();
    const zipBtn = screen.getAllByRole('button').find((b) => /zip archive/i.test(b.textContent ?? ''));
    expect(zipBtn).toBeDefined();
    fireEvent.click(zipBtn!);
    await waitFor(() => expect(screen.getAllByText(/drag & drop a zip archive/i).length).toBeGreaterThanOrEqual(1));
  });

  it('shows batch result table after inference', async () => {
    setupModels();
    mock.onPost('/predict/batch').reply(200, { success: true, data: makeBatchResult() });
    const user = userEvent.setup();
    renderPage();
    const input = await screen.findByLabelText(/upload mri images/i);
    await user.upload(input, makeFile());
    await user.click(screen.getByRole('button', { name: /run inference/i }));
    await waitFor(() => expect(screen.getByTestId('prediction-table')).toBeInTheDocument(), { timeout: 5000 });
  });

  it('shows error message on batch failure', async () => {
    setupModels();
    mock.onPost('/predict/batch').reply(400, { detail: 'No images provided' });
    const user = userEvent.setup();
    renderPage();
    const input = await screen.findByLabelText(/upload mri images/i);
    await user.upload(input, makeFile());
    await user.click(screen.getByRole('button', { name: /run inference/i }));
    await waitFor(() => expect(screen.getByText(/no images provided/i)).toBeInTheDocument(), { timeout: 5000 });
  });

  it('renders model selector', async () => {
    setupModels();
    renderPage();
    await waitFor(() => expect(screen.getByTestId('model-selector')).toBeInTheDocument());
  });
});
