/**
 * src/pages/Dashboard.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import Dashboard from './Dashboard';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const renderPage = () =>
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

const HEALTH = {
  success: true, status: 'ok',
  service: 'Brain Tumour Detection AI Service',
  version: '1.0.0',
  timestamp: '2024-01-01T12:00:00Z',
  environment: 'development',
  active_model: 'efficientnet',
  class_names: ['glioma', 'meningioma', 'notumor', 'pituitary'],
  image_size: 224,
  python_version: '3.11.0',
  models_available: { cnn: false, vgg16: false, resnet50: false, efficientnet: true },
};

describe('Dashboard', () => {
  it('renders hero heading', () => {
    mock.onGet('/health').reply(200, HEALTH);
    renderPage();
    expect(screen.getByText(/brain tumour detection/i)).toBeInTheDocument();
  });

  it('renders all 6 quick-action cards', () => {
    mock.onGet('/health').reply(200, HEALTH);
    renderPage();
    expect(screen.getAllByText(/single prediction/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/batch prediction/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/train a model/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/experiments/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/dataset manager/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/model manager/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows Online status when service responds ok', async () => {
    mock.onGet('/health').reply(200, HEALTH);
    renderPage();
    await waitFor(() => expect(screen.getByText(/online/i)).toBeInTheDocument());
  });

  it('shows active model from health response', async () => {
    mock.onGet('/health').reply(200, HEALTH);
    renderPage();
    await waitFor(() => {
      const els = screen.getAllByText(/efficientnet/i);
      expect(els.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows service unavailable message on error', async () => {
    mock.onGet('/health').networkError();
    renderPage();
    await waitFor(() => expect(screen.getByText(/could not reach/i)).toBeInTheDocument());
  });

  it('shows image size from health', async () => {
    mock.onGet('/health').reply(200, HEALTH);
    renderPage();
    await waitFor(() => expect(screen.getByText(/224 × 224/i)).toBeInTheDocument());
  });
});
