/**
 * src/components/ProbabilityChart.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProbabilityChart from './ProbabilityChart';
import { makePredictionResult } from '@/test/fixtures';

// Recharts uses SVG — just verify it mounts and testid exists
describe('ProbabilityChart', () => {
  it('renders without crashing', () => {
    render(<ProbabilityChart result={makePredictionResult()} />);
    expect(screen.getByTestId('probability-chart')).toBeInTheDocument();
  });

  it('renders class probabilities heading', () => {
    render(<ProbabilityChart result={makePredictionResult()} />);
    expect(screen.getByText(/class probabilities/i)).toBeInTheDocument();
  });
});
