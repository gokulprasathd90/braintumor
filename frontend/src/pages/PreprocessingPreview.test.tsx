/**
 * src/pages/PreprocessingPreview.test.tsx
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import PreprocessingPreview from './PreprocessingPreview';
import { makePreviewResult, makeFile } from '@/test/fixtures';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

const renderPage = () =>
  render(<MemoryRouter><PreprocessingPreview /></MemoryRouter>);

describe('PreprocessingPreview', () => {
  it('renders heading', () => {
    renderPage();
    expect(screen.getByText('Preprocessing Preview')).toBeInTheDocument();
  });

  it('renders upload panel initially', () => {
    renderPage();
    expect(screen.getByText(/drag & drop your mri image/i)).toBeInTheDocument();
  });

  it('renders augmentation options', () => {
    renderPage();
    expect(screen.getByRole('checkbox', { name: /include augmentation/i })).toBeInTheDocument();
  });

  it('shows quality report after upload', async () => {
    mock.onPost('/preprocess/preview').reply(200, {
      success: true, data: makePreviewResult(), message: 'OK',
    });
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText(/upload mri image/i);
    await user.upload(input, makeFile());
    await waitFor(() => expect(screen.getByTestId('quality-check-panel')).toBeInTheDocument(), { timeout: 5000 });
  });

  it('shows preprocessed image after upload', async () => {
    mock.onPost('/preprocess/preview').reply(200, {
      success: true, data: makePreviewResult(), message: 'OK',
    });
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText(/upload mri image/i);
    await user.upload(input, makeFile());
    await waitFor(() => expect(screen.getByAltText(/preprocessed mri/i)).toBeInTheDocument(), { timeout: 5000 });
  });

  it('shows error on preview failure', async () => {
    mock.onPost('/preprocess/preview').reply(400, { detail: 'Image failed quality checks' });
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText(/upload mri image/i);
    await user.upload(input, makeFile());
    await waitFor(() => expect(screen.getByText(/image failed quality checks/i)).toBeInTheDocument(), { timeout: 5000 });
  });
});
