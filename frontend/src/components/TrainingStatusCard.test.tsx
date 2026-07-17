/**
 * src/components/TrainingStatusCard.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TrainingStatusCard from './TrainingStatusCard';
import { makeTrainingJob, makeCompletedJob } from '@/test/fixtures';

describe('TrainingStatusCard', () => {
  it('renders testid', () => {
    render(<TrainingStatusCard job={makeTrainingJob()} />);
    expect(screen.getByTestId('training-status-card')).toBeInTheDocument();
  });

  it('shows Running status for running job', () => {
    render(<TrainingStatusCard job={makeTrainingJob({ status: 'running' })} />);
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('shows Completed status for completed job', () => {
    render(<TrainingStatusCard job={makeCompletedJob()} />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('shows Failed status for failed job', () => {
    render(<TrainingStatusCard job={makeTrainingJob({ status: 'failed', error: 'OOM error' })} />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows error message when job has error', () => {
    render(<TrainingStatusCard job={makeTrainingJob({ status: 'failed', error: 'GPU out of memory' })} />);
    expect(screen.getByText(/gpu out of memory/i)).toBeInTheDocument();
  });

  it('shows val accuracy when completed', () => {
    render(<TrainingStatusCard job={makeCompletedJob()} />);
    expect(screen.getByText('97.30%')).toBeInTheDocument();
  });

  it('shows polling indicator when polling=true', () => {
    render(<TrainingStatusCard job={makeTrainingJob()} polling />);
    expect(screen.getByText(/polling/i)).toBeInTheDocument();
  });

  it('shows experiment_id when present', () => {
    render(<TrainingStatusCard job={makeTrainingJob()} />);
    expect(screen.getByText(/efficientnet-20240101/i)).toBeInTheDocument();
  });
});
