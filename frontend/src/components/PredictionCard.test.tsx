/**
 * src/components/PredictionCard.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PredictionCard from './PredictionCard';
import { makePredictionResult } from '@/test/fixtures';

describe('PredictionCard', () => {
  it('renders predicted class name', () => {
    render(<PredictionCard result={makePredictionResult()} />);
    // the badge span contains "Glioma" (capitalised)
    expect(screen.getAllByText(/glioma/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders confidence as percentage', () => {
    render(<PredictionCard result={makePredictionResult()} />);
    // confidence appears as "85.0%" in the large number
    expect(screen.getAllByText(/85\.0/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows high confidence badge when is_high_confidence=true', () => {
    render(<PredictionCard result={makePredictionResult({ is_high_confidence: true })} />);
    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  });

  it('does not show high confidence badge when false', () => {
    render(<PredictionCard result={makePredictionResult({ is_high_confidence: false })} />);
    expect(screen.queryByText(/high confidence/i)).not.toBeInTheDocument();
  });

  it('renders top-k list when showTopK=true and k>1', () => {
    render(<PredictionCard result={makePredictionResult()} showTopK />);
    expect(screen.getByText(/meningioma/i)).toBeInTheDocument();
  });

  it('does not render top-k when showTopK=false', () => {
    render(<PredictionCard result={makePredictionResult()} showTopK={false} />);
    expect(screen.queryByText(/meningioma/i)).not.toBeInTheDocument();
  });

  it('renders model name in footer', () => {
    render(<PredictionCard result={makePredictionResult()} />);
    expect(screen.getByText('efficientnet')).toBeInTheDocument();
  });

  it('renders timing in footer when showTiming=true', () => {
    render(<PredictionCard result={makePredictionResult({ timing_ms: 99.5 })} showTiming />);
    // timing shown as "99 ms" inside a span
    expect(screen.getByText(/\d+ ms/i)).toBeInTheDocument();
  });

  it('renders notumor class with green styling', () => {
    const { container } = render(
      <PredictionCard result={makePredictionResult({ predicted_class: 'notumor', predicted_class_index: 2 })} />
    );
    expect(container.firstChild).toHaveClass('bg-green-50');
  });

  it('has testid attribute', () => {
    render(<PredictionCard result={makePredictionResult()} />);
    expect(screen.getByTestId('prediction-card')).toBeInTheDocument();
  });
});
