/**
 * src/pages/Experiments.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import Experiments from './Experiments';
import { makeExperiment } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const EXPS = [
  makeExperiment({ experiment_id: 'exp-001', architecture: 'efficientnet' }),
  makeExperiment({ experiment_id: 'exp-002', architecture: 'resnet50' }),
];

const renderPage = () =>
  render(<MemoryRouter><Experiments /></MemoryRouter>);

describe('Experiments', () => {
  it('renders heading', async () => {
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: EXPS, total: 2 });
    renderPage();
    expect(screen.getByText('Experiments')).toBeInTheDocument();
  });

  it('renders experiment list after loading', async () => {
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: EXPS, total: 2 });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('experiment-list')).toBeInTheDocument());
    // Multiple "efficientnet" texts expected (filter column, badge, etc.)
    expect(screen.getAllByText(/efficientnet/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty state when no experiments', async () => {
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: [], total: 0 });
    renderPage();
    await waitFor(() => expect(screen.getByText(/no experiments yet/i)).toBeInTheDocument());
  });

  it('shows detail pane instruction before selection', async () => {
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: EXPS, total: 2 });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('experiment-list')).toBeInTheDocument());
    expect(screen.getByText(/click an experiment/i)).toBeInTheDocument();
  });

  it('loads experiment detail on row click', async () => {
    // Register the specific detail mock BEFORE the list regex so it takes priority
    mock.onGet('/train/experiments/exp-001').reply(200, { success: true, data: EXPS[0] });
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: EXPS, total: 2 });
    renderPage();
    // Wait for the experiment list to render; architecture appears in both the
    // filter <select> options and the table cells, so getAllByText is required.
    await waitFor(() => expect(screen.getAllByText('efficientnet').length).toBeGreaterThanOrEqual(1));
    // Click the first table-cell occurrence (the <td>, not the <option>)
    const cells = screen.getAllByText('efficientnet');
    const tableCell = cells.find((el) => el.tagName.toLowerCase() === 'td');
    fireEvent.click(tableCell ?? cells[0]);
    await waitFor(() => expect(screen.getByText('Experiment Detail')).toBeInTheDocument(), { timeout: 3000 });
  });

  it('renders Refresh button', async () => {
    mock.onGet(/\/train\/experiments/).reply(200, { success: true, data: [], total: 0 });
    renderPage();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });
});
