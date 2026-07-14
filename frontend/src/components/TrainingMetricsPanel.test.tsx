/**
 * src/components/TrainingMetricsPanel.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TrainingMetricsPanel from './TrainingMetricsPanel';
import type { TrainingMetrics } from '@/types';

const BASE_DATA: TrainingMetrics = {
  timestamp: '2024-07-14T12:00:00Z',
  total_jobs: 7,
  queued_jobs: 0,
  running_jobs: 0,
  completed_jobs: 6,
  failed_jobs: 1,
  avg_job_duration_s: 1800.0,
  architecture_counts: { efficientnet: 4, resnet50: 2, cnn: 1 },
  recent_jobs: [
    {
      job_id: 'job-abc-123-def-456',
      status: 'completed',
      architecture: 'efficientnet',
      created_at: '2024-07-14T10:00:00Z',
      started_at: '2024-07-14T10:01:00Z',
      finished_at: '2024-07-14T10:31:00Z',
      duration_s: 1800.0,
    },
  ],
  total_experiments: 6,
  best_val_accuracy: 0.9732,
  recent_experiments: [
    {
      experiment_id: 'efficientnet-20240714-1234abcd',
      architecture: 'efficientnet',
      status: 'completed',
      best_val_accuracy: 0.9732,
      epochs_trained: 38,
      duration_s: 1810.5,
      created_at: '2024-07-14T10:00:00Z',
    },
  ],
};

describe('TrainingMetricsPanel', () => {
  it('renders with testid', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByTestId('training-metrics-panel')).toBeInTheDocument();
  });

  it('shows total jobs count', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('shows completed jobs count', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('shows failed jobs count', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows best val accuracy', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    // Appears in both the stat card and the experiments table
    expect(screen.getAllByText('97.32%').length).toBeGreaterThanOrEqual(1);
  });

  it('shows architecture bar chart section', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Jobs by Architecture')).toBeInTheDocument();
  });

  it('shows recent jobs table', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Recent Jobs')).toBeInTheDocument();
  });

  it('shows completed status badge in recent jobs', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getAllByText('completed').length).toBeGreaterThanOrEqual(1);
  });

  it('shows duration formatted', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('30.0 min')).toBeInTheDocument();
  });

  it('shows recent experiments table', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('Recent Experiments')).toBeInTheDocument();
  });

  it('shows epochs in experiments table', () => {
    render(<TrainingMetricsPanel data={BASE_DATA} />);
    expect(screen.getByText('38')).toBeInTheDocument();
  });

  it('shows dash for null best_val_accuracy', () => {
    render(<TrainingMetricsPanel data={{ ...BASE_DATA, best_val_accuracy: null }} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('hides arch chart when counts are empty', () => {
    render(<TrainingMetricsPanel data={{ ...BASE_DATA, architecture_counts: {} }} />);
    expect(screen.queryByText('Jobs by Architecture')).not.toBeInTheDocument();
  });
});
