/**
 * src/components/ExperimentList.test.tsx
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ExperimentList from './ExperimentList';
import { makeExperiment } from '@/test/fixtures';

const EXPERIMENTS = [
  makeExperiment({ experiment_id: 'exp-001', architecture: 'efficientnet', status: 'completed' }),
  makeExperiment({ experiment_id: 'exp-002', architecture: 'resnet50',     status: 'failed'    }),
  makeExperiment({ experiment_id: 'exp-003', architecture: 'vgg16',        status: 'running'   }),
];

describe('ExperimentList', () => {
  it('renders testid', () => {
    render(<ExperimentList experiments={EXPERIMENTS} />);
    expect(screen.getByTestId('experiment-list')).toBeInTheDocument();
  });

  it('renders a row for each experiment', () => {
    render(<ExperimentList experiments={EXPERIMENTS} />);
    expect(screen.getByText('efficientnet')).toBeInTheDocument();
    expect(screen.getByText('resnet50')).toBeInTheDocument();
    expect(screen.getByText('vgg16')).toBeInTheDocument();
  });

  it('shows status badge for each row', () => {
    render(<ExperimentList experiments={EXPERIMENTS} />);
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('shows empty state when experiments array is empty', () => {
    render(<ExperimentList experiments={[]} />);
    expect(screen.getByText(/no experiments yet/i)).toBeInTheDocument();
  });

  it('shows loading skeleton when loading=true', () => {
    const { container } = render(<ExperimentList experiments={[]} loading />);
    const pulses = container.querySelectorAll('.animate-pulse');
    expect(pulses.length).toBeGreaterThan(0);
  });

  it('calls onSelect when a row is clicked', () => {
    const onSelect = vi.fn();
    render(<ExperimentList experiments={EXPERIMENTS} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('efficientnet'));
    expect(onSelect).toHaveBeenCalledWith(EXPERIMENTS[0]);
  });

  it('highlights selected row', () => {
    render(<ExperimentList experiments={EXPERIMENTS} onSelect={vi.fn()} selectedId="exp-002" />);
    const row = screen.getByText('resnet50').closest('tr');
    expect(row).toHaveClass('bg-blue-50');
  });

  it('shows val accuracy when available', () => {
    render(<ExperimentList experiments={EXPERIMENTS} />);
    expect(screen.getAllByText(/97\.30%/).length).toBeGreaterThan(0);
  });
});
