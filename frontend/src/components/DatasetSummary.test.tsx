/**
 * src/components/DatasetSummary.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DatasetSummary from './DatasetSummary';
import { makeDatasetInfo } from '@/test/fixtures';

describe('DatasetSummary', () => {
  it('renders testid', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getByTestId('dataset-summary')).toBeInTheDocument();
  });

  it('shows train split count', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getByText('2,184')).toBeInTheDocument();
  });

  it('shows val split count', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getAllByText('467').length).toBeGreaterThanOrEqual(1);
  });

  it('shows test split count', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    // val and test both 467
    const els = screen.getAllByText('467');
    expect(els.length).toBeGreaterThanOrEqual(2);
  });

  it('shows total images', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getByText('3,118')).toBeInTheDocument();
  });

  it('shows balanced indicator', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getByText('Yes')).toBeInTheDocument();
  });

  it('renders per-class table when per_class_counts provided', () => {
    render(<DatasetSummary info={makeDatasetInfo()} />);
    expect(screen.getByText(/glioma/i)).toBeInTheDocument();
    expect(screen.getByText(/meningioma/i)).toBeInTheDocument();
  });
});
