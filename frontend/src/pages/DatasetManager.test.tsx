/**
 * src/pages/DatasetManager.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import DatasetManager from './DatasetManager';
import { makeDatasetInfo, makeValidationReport } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const renderPage = () =>
  render(<MemoryRouter><DatasetManager /></MemoryRouter>);

describe('DatasetManager', () => {
  it('renders heading', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: 'not prepared' });
    renderPage();
    expect(screen.getByText('Dataset Manager')).toBeInTheDocument();
  });

  it('shows DatasetSummary when info available', async () => {
    mock.onGet('/dataset/info').reply(200, {
      success: true, data: makeDatasetInfo(), message: '',
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('dataset-summary')).toBeInTheDocument());
  });

  it('shows "no prepared dataset" message on 404', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: 'no dataset_info.json' });
    renderPage();
    await waitFor(() => expect(screen.getByText(/no prepared dataset/i)).toBeInTheDocument());
  });

  it('shows validation result after clicking Run Validation', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: 'not prepared' });
    mock.onPost('/dataset/validate').reply(200, {
      success: true, data: makeValidationReport(true), message: '',
    });
    renderPage();
    await waitFor(() => expect(screen.getByRole('button', { name: /run validation/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /run validation/i }));
    await waitFor(() => expect(screen.getByText(/✓ dataset is valid/i)).toBeInTheDocument(), { timeout: 3000 });
  });

  it('renders train ratio input', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    renderPage();
    expect(screen.getByDisplayValue('0.7')).toBeInTheDocument();
  });

  it('renders Prepare Dataset button', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    renderPage();
    expect(screen.getByRole('button', { name: /prepare dataset/i })).toBeInTheDocument();
  });

  it('calls prepare endpoint on button click', async () => {
    mock.onGet('/dataset/info').reply(404, { detail: '' });
    mock.onPost('/dataset/prepare').reply(200, {
      success: true, data: makeDatasetInfo(), message: 'Done',
    });
    renderPage();
    await waitFor(() => expect(screen.getByRole('button', { name: /prepare dataset/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /prepare dataset/i }));
    await waitFor(() => expect(screen.getByTestId('dataset-summary')).toBeInTheDocument(), { timeout: 3000 });
  });
});
