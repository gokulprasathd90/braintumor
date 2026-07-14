/**
 * src/pages/Training.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import Training from './Training';
import { makeTrainingJob } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => { mock.reset(); });
afterEach(() => { mock.reset(); vi.useRealTimers(); });

const renderPage = () =>
  render(<MemoryRouter><Training /></MemoryRouter>);

describe('Training', () => {
  it('renders heading', () => {
    renderPage();
    expect(screen.getByText('Train a Model')).toBeInTheDocument();
  });

  it('renders training config fields', () => {
    renderPage();
    expect(screen.getByLabelText(/epochs/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/batch size/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/learning rate/i)).toBeInTheDocument();
  });

  it('renders Start Training button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /start training job/i })).toBeInTheDocument();
  });

  it('renders fine-tune toggle checkbox', () => {
    renderPage();
    expect(screen.getByRole('checkbox', { name: /fine-tuning/i })).toBeInTheDocument();
  });

  it('shows TrainingStatusCard after job starts', async () => {
    mock.onPost('/train/start').reply(202, {
      success: true, message: 'queued', job_id: 'j1', experiment_id: 'exp-1',
    });
    mock.onGet('/train/status/j1').reply(200, {
      success: true, data: makeTrainingJob({ job_id: 'j1' }),
    });
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /start training job/i }));
    await waitFor(() => expect(screen.getByTestId('training-status-card')).toBeInTheDocument(), { timeout: 5000 });
  });

  it('shows error when start fails', async () => {
    mock.onPost('/train/start').reply(422, { detail: 'Invalid architecture' });
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /start training job/i }));
    await waitFor(() => expect(screen.getByText(/invalid architecture/i)).toBeInTheDocument(), { timeout: 3000 });
  });

  it('epochs field has default value 30', () => {
    renderPage();
    expect((screen.getByLabelText(/epochs/i) as HTMLInputElement).value).toBe('30');
  });
});
