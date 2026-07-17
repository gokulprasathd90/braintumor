/**
 * src/components/BatchUpload.test.tsx
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BatchUpload from './BatchUpload';
import { makeFile } from '@/test/fixtures';

describe('BatchUpload — files mode', () => {
  it('renders drop zone', () => {
    render(<BatchUpload mode="files" onSubmit={vi.fn()} />);
    expect(screen.getByTestId('batch-upload')).toBeInTheDocument();
    expect(screen.getByText(/drag & drop mri images/i)).toBeInTheDocument();
  });

  it('shows file count after drop', async () => {
    const user = userEvent.setup();
    render(<BatchUpload mode="files" onSubmit={vi.fn()} />);
    const input = screen.getByLabelText(/upload mri images/i);
    const file = makeFile();
    await user.upload(input, file);
    expect(screen.getByText(/1 image queued/i)).toBeInTheDocument();
  });

  it('shows Run Inference button after files selected', async () => {
    const user = userEvent.setup();
    render(<BatchUpload mode="files" onSubmit={vi.fn()} />);
    const input = screen.getByLabelText(/upload mri images/i);
    await user.upload(input, makeFile());
    expect(screen.getByRole('button', { name: /run inference/i })).toBeInTheDocument();
  });

  it('calls onSubmit with files array on submit', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<BatchUpload mode="files" onSubmit={onSubmit} />);
    const input = screen.getByLabelText(/upload mri images/i);
    await user.upload(input, makeFile());
    await user.click(screen.getByRole('button', { name: /run inference/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('disables interactions when loading=true', () => {
    render(<BatchUpload mode="files" onSubmit={vi.fn()} loading />);
    const dropzone = screen.getByTestId('batch-upload').querySelector('div[class*="opacity-60"]');
    expect(dropzone).toBeInTheDocument();
  });
});

describe('BatchUpload — zip mode', () => {
  it('renders ZIP instructions', () => {
    render(<BatchUpload mode="zip" onSubmit={vi.fn()} />);
    expect(screen.getByText(/drag & drop a zip archive/i)).toBeInTheDocument();
  });
});
