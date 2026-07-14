/**
 * src/components/InferenceMetricsPanel.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import InferenceMetricsPanel from './InferenceMetricsPanel';
import type { InferenceMetrics } from '@/types';

const BASE_DATA: InferenceMetrics = {
  timestamp: '2024-07-14T12:00:00Z',
  started_at: '2024-07-14T10:00:00Z',
  total_predictions: 142,
  succeeded: 138,
  failed: 4,
  success_rate: 0.9718,
  per_model_counts: { efficientnet: 138 },
  avg_latency_ms: 38.4,
  min_latency_ms: 12.1,
  max_latency_ms: 240.0,
  p95_latency_ms: 74.1,
  confidence_distribution: {
    buckets: ['<50%', '50–70%', '70–80%', '80–90%', '90–95%', '95–100%'],
    counts:  [1,      2,        3,        10,       20,       102],
  },
  class_distribution: { glioma: 67, notumor: 44, meningioma: 21, pituitary: 10 },
  top_classes: [{ class_name: 'glioma', count: 67 }, { class_name: 'notumor', count: 44 }],
  batch_runs: 3,
  batch_images_processed: 45,
  batch_succeeded: 43,
  batch_failed: 2,
  recent_predictions: [
    {
      image_id: 'img-001',
      model_name: 'efficientnet',
      predicted_class: 'glioma',
      confidence: 0.92,
      timing_ms: 38.5,
      success: true,
      timestamp: '2024-07-14T12:00:00Z',
    },
  ],
};

describe('InferenceMetricsPanel', () => {
  it('renders the panel with testid', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByTestId('inference-metrics-panel')).toBeInTheDocument();
  });

  it('shows total predictions count', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('142')).toBeInTheDocument();
  });

  it('shows success rate', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('97.2%')).toBeInTheDocument();
  });

  it('shows average latency', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText(/38\.4 ms/)).toBeInTheDocument();
  });

  it('shows p95 latency in sub', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText(/p95: 74\.1 ms/)).toBeInTheDocument();
  });

  it('shows batch images processed', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('shows model name badges', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getAllByText(/efficientnet/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows confidence distribution section', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Confidence Distribution')).toBeInTheDocument();
  });

  it('shows class distribution section', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Class Distribution')).toBeInTheDocument();
  });

  it('shows recent predictions table', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Recent Predictions')).toBeInTheDocument();
    expect(screen.getByText('glioma')).toBeInTheDocument();
  });

  it('shows ok status badge in recent predictions', () => {
    render(<InferenceMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('ok')).toBeInTheDocument();
  });

  it('shows null latency as dash', () => {
    render(<InferenceMetricsPanel data={{ ...BASE_DATA, avg_latency_ms: null }} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('hides confidence section when no predictions', () => {
    render(<InferenceMetricsPanel data={{ ...BASE_DATA, total_predictions: 0 }} />);
    expect(screen.queryByText('Confidence Distribution')).not.toBeInTheDocument();
  });
});
