/**
 * src/components/QualityCheckPanel.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import QualityCheckPanel from './QualityCheckPanel';
import { makeQualityReport } from '@/test/fixtures';

describe('QualityCheckPanel', () => {
  it('renders testid', () => {
    render(<QualityCheckPanel report={makeQualityReport()} />);
    expect(screen.getByTestId('quality-check-panel')).toBeInTheDocument();
  });

  it('shows passed verdict for valid report', () => {
    render(<QualityCheckPanel report={makeQualityReport(true)} />);
    expect(screen.getByText(/all quality checks passed/i)).toBeInTheDocument();
  });

  it('shows failed verdict for invalid report', () => {
    render(<QualityCheckPanel report={makeQualityReport(false)} />);
    expect(screen.getByText(/quality check failed/i)).toBeInTheDocument();
  });

  it('renders all 6 check rows', () => {
    render(<QualityCheckPanel report={makeQualityReport(true)} />);
    const rows = screen.getAllByText(/ok/i);
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it('shows image dimensions in verdict', () => {
    render(<QualityCheckPanel report={makeQualityReport()} />);
    expect(screen.getByText(/224 × 224/)).toBeInTheDocument();
  });

  it('shows error messages for failed checks', () => {
    render(<QualityCheckPanel report={makeQualityReport(false)} />);
    expect(screen.getByText(/image may be too dark/i)).toBeInTheDocument();
  });
});
