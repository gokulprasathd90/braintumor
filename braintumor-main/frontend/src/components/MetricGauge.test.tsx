/**
 * src/components/MetricGauge.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MetricGauge from './MetricGauge';

describe('MetricGauge', () => {
  it('renders the label', () => {
    render(<MetricGauge label="CPU" value={42} />);
    expect(screen.getByText('CPU')).toBeInTheDocument();
  });

  it('renders the percentage value', () => {
    render(<MetricGauge label="RAM" value={75} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('renders N/A when value is null', () => {
    render(<MetricGauge label="Disk" value={null} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('has aria-label with value', () => {
    render(<MetricGauge label="GPU" value={88} />);
    expect(screen.getByLabelText(/GPU: 88%/)).toBeInTheDocument();
  });

  it('has aria-label with N/A when null', () => {
    render(<MetricGauge label="CPU" value={null} />);
    expect(screen.getByLabelText(/CPU: N\/A/)).toBeInTheDocument();
  });

  it('renders as data-testid metric-gauge', () => {
    render(<MetricGauge label="CPU" value={50} />);
    expect(screen.getByTestId('metric-gauge')).toBeInTheDocument();
  });

  it('accepts custom unit', () => {
    render(<MetricGauge label="Temp" value={65} unit="°C" />);
    expect(screen.getByText('65°C')).toBeInTheDocument();
  });

  it('rounds decimal values', () => {
    render(<MetricGauge label="CPU" value={34.7} />);
    expect(screen.getByText('35%')).toBeInTheDocument();
  });

  it('clamps value at 100 for arc rendering', () => {
    render(<MetricGauge label="CPU" value={120} />);
    // Should not crash and renders the number as-given in text
    expect(screen.getByLabelText(/CPU: 120%/)).toBeInTheDocument();
  });
});
