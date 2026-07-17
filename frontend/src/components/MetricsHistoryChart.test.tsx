/**
 * src/components/MetricsHistoryChart.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MetricsHistoryChart, { type MetricLine } from './MetricsHistoryChart';
import type { DashboardHistoryPoint } from '@/types';

const METRICS: MetricLine[] = [
  { key: 'cpu_percent', label: 'CPU %', color: '#3b82f6', format: (v) => `${v}%` },
  { key: 'ram_percent', label: 'RAM %', color: '#8b5cf6' },
];

const POINTS: DashboardHistoryPoint[] = [
  { timestamp: '2024-07-14T10:00:00Z', cpu_percent: 30, ram_percent: 50 },
  { timestamp: '2024-07-14T11:00:00Z', cpu_percent: 35, ram_percent: 55 },
  { timestamp: '2024-07-14T12:00:00Z', cpu_percent: 40, ram_percent: 60 },
];

describe('MetricsHistoryChart', () => {
  it('renders the chart testid when data is present', () => {
    render(<MetricsHistoryChart data={POINTS} metrics={METRICS} />);
    expect(screen.getByTestId('metrics-history-chart')).toBeInTheDocument();
  });

  it('renders empty state when data is empty', () => {
    render(<MetricsHistoryChart data={[]} metrics={METRICS} />);
    expect(screen.getByTestId('metrics-history-chart-empty')).toBeInTheDocument();
  });

  it('shows custom empty message', () => {
    render(<MetricsHistoryChart data={[]} metrics={METRICS} emptyMessage="No data yet" />);
    expect(screen.getByText('No data yet')).toBeInTheDocument();
  });

  it('renders title when provided', () => {
    render(<MetricsHistoryChart data={POINTS} metrics={METRICS} title="System History" />);
    expect(screen.getByText('System History')).toBeInTheDocument();
  });

  it('does not render title section when not provided', () => {
    const { container } = render(<MetricsHistoryChart data={POINTS} metrics={METRICS} />);
    // No <p> with title content
    expect(container.querySelector('p')).toBeNull();
  });

  it('handles single data point without error', () => {
    const single: DashboardHistoryPoint[] = [
      { timestamp: '2024-07-14T10:00:00Z', cpu_percent: 30 },
    ];
    render(<MetricsHistoryChart data={single} metrics={METRICS} />);
    expect(screen.getByTestId('metrics-history-chart')).toBeInTheDocument();
  });

  it('handles more than 120 points by thinning data', () => {
    const manyPoints = Array.from({ length: 200 }, (_, i) => ({
      timestamp: `2024-07-14T${String(i % 24).padStart(2, '0')}:00:00Z`,
      cpu_percent: i % 100,
    }));
    render(<MetricsHistoryChart data={manyPoints} metrics={METRICS} />);
    expect(screen.getByTestId('metrics-history-chart')).toBeInTheDocument();
  });
});
