/**
 * src/pages/SinglePrediction.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import SinglePrediction from './SinglePrediction';
import { makePredictionResult, makeFile, makeModelList, makeCacheStats, makeActiveModel } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const setupModels = () => {
  mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
  mock.onGet('/models/active').reply(200, { success: true, data: makeActiveModel() });
};

const renderPage = () =>
  render(<MemoryRouter><SinglePrediction /></MemoryRouter>);

describe('SinglePrediction', () => {
  it('renders heading', () => {
    setupModels();
    renderPage();
    expect(screen.getByText('Single Prediction')).toBeInTheDocument();
  });

  it('renders inference settings panel', async () => {
    setupModels();
    renderPage();
    await waitFor(() => expect(screen.getByText('Inference Settings')).toBeInTheDocument());
  });

  it('renders model selector', async () => {
    setupModels();
    renderPage();
    await waitFor(() => expect(screen.getByTestId('model-selector')).toBeInTheDocument());
  });

  it('renders upload panel', async () => {
    setupModels();
    renderPage();
    expect(screen.getByText(/drag & drop your mri image/i)).toBeInTheDocument();
  });

  it('shows prediction result after upload', async () => {
    setupModels();
    mock.onPost('/predict/image').reply(200, { success: true, data: makePredictionResult() });
    const user = userEvent.setup();
    renderPage();
    const input = await screen.findByLabelText(/upload mri image/i);
    await user.upload(input, makeFile());
    await waitFor(() => expect(screen.getByTestId('prediction-card')).toBeInTheDocument(), { timeout: 5000 });
  });

  it('shows error card when prediction fails', async () => {
    setupModels();
    mock.onPost('/predict/image').reply(404, { detail: 'No model weights found' });
    const user = userEvent.setup();
    renderPage();
    const input = await screen.findByLabelText(/upload mri image/i);
    await user.upload(input, makeFile());
    await waitFor(() => expect(screen.getByText(/no model weights found/i)).toBeInTheDocument(), { timeout: 5000 });
  });

  it('renders top-k selector', async () => {
    setupModels();
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/top-k/i)).toBeInTheDocument());
  });

  it('renders Grad-CAM checkbox', async () => {
    setupModels();
    renderPage();
    await waitFor(() => expect(screen.getByRole('checkbox', { name: /generate grad-cam/i })).toBeInTheDocument());
  });
});
