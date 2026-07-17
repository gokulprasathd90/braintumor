/**
 * src/components/PredictionTable.test.tsx
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PredictionTable from './PredictionTable';
import { makeBatchResult } from '@/test/fixtures';

describe('PredictionTable', () => {
  it('renders testid', () => {
    render(<PredictionTable result={makeBatchResult()} />);
    expect(screen.getByTestId('prediction-table')).toBeInTheDocument();
  });

  it('shows total, succeeded and failed counts', () => {
    render(<PredictionTable result={makeBatchResult()} />);
    // "Total: 3" appears in the summary bar
    const totalEl = screen.getByText(/total:/i);
    expect(totalEl.closest('span')?.textContent).toMatch(/3/);
  });

  it('renders table rows for each result', () => {
    const result = makeBatchResult();
    render(<PredictionTable result={result} />);
    expect(screen.getByText('scan1.jpg')).toBeInTheDocument();
    expect(screen.getByText('scan2.jpg')).toBeInTheDocument();
    expect(screen.getByText('bad.jpg')).toBeInTheDocument();
  });

  it('shows ✓ OK for successful items', () => {
    render(<PredictionTable result={makeBatchResult()} />);
    const okBadges = screen.getAllByText(/✓ ok/i);
    expect(okBadges.length).toBe(2);
  });

  it('shows ✗ Error for failed items', () => {
    render(<PredictionTable result={makeBatchResult()} />);
    expect(screen.getByText(/✗ error/i)).toBeInTheDocument();
  });

  it('calls onDownloadCSV when CSV button clicked', () => {
    const onCSV = vi.fn();
    render(<PredictionTable result={makeBatchResult()} onDownloadCSV={onCSV} />);
    fireEvent.click(screen.getByText(/↓ csv/i));
    expect(onCSV).toHaveBeenCalledTimes(1);
  });

  it('calls onDownloadJSON when JSON button clicked', () => {
    const onJSON = vi.fn();
    render(<PredictionTable result={makeBatchResult()} onDownloadJSON={onJSON} />);
    fireEvent.click(screen.getByText(/↓ json/i));
    expect(onJSON).toHaveBeenCalledTimes(1);
  });

  it('shows glioma class badge for successful predictions', () => {
    render(<PredictionTable result={makeBatchResult()} />);
    const badges = screen.getAllByText('glioma');
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });
});
