/**
 * src/pages/ModelManager.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import ModelManager from './ModelManager';
import { makeModelList, makeCacheStats, makeActiveModel } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const setupOk = () => {
  mock.onGet('/models').reply(200, { success: true, data: makeModelList(), cache_stats: makeCacheStats() });
  mock.onGet('/models/active').reply(200, { success: true, data: makeActiveModel() });
};

const renderPage = () =>
  render(<MemoryRouter><ModelManager /></MemoryRouter>);

describe('ModelManager', () => {
  it('renders heading', () => {
    setupOk();
    renderPage();
    expect(screen.getByText('Model Manager')).toBeInTheDocument();
  });

  it('shows active model panel', async () => {
    setupOk();
    renderPage();
    await waitFor(() => expect(screen.getByText('Active Model')).toBeInTheDocument());
    // "efficientnet" appears in both the Active Model panel and the All Models list
    expect(screen.getAllByText(/efficientnet/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows cache statistics', async () => {
    setupOk();
    renderPage();
    await waitFor(() => expect(screen.getByText('Cache Statistics')).toBeInTheDocument());
    expect(screen.getByText('4')).toBeInTheDocument(); // capacity
  });

  it('renders a row for each model', async () => {
    setupOk();
    renderPage();
    await waitFor(() => expect(screen.getByText('All Models')).toBeInTheDocument());
    expect(screen.getByText('cnn')).toBeInTheDocument();
    expect(screen.getByText('vgg16')).toBeInTheDocument();
    expect(screen.getByText('resnet50')).toBeInTheDocument();
  });

  it('shows Hot Reload button for available models', async () => {
    setupOk();
    renderPage();
    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /hot reload/i });
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it('calls reload endpoint on Hot Reload click', async () => {
    setupOk();
    mock.onPost('/models/reload').reply(200, {
      success: true, message: 'reloaded', model_name: 'efficientnet',
    });
    renderPage();
    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /hot reload/i });
      expect(buttons.length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getAllByRole('button', { name: /hot reload/i })[0]);
    await waitFor(() => expect(mock.history.post.length).toBe(1));
  });

  it('shows Refresh button', () => {
    setupOk();
    renderPage();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });
});
