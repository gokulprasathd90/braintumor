/**
 * src/components/AlertsBanner.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AlertsBanner from './AlertsBanner';
import type { DashboardAlert } from '@/types';

describe('AlertsBanner', () => {
  it('renders nothing when alerts array is empty', () => {
    const { container } = render(<AlertsBanner alerts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders a warning alert', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'system', message: 'CPU usage high: 82%' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText(/CPU usage high: 82%/)).toBeInTheDocument();
    expect(screen.getByText(/warning/i)).toBeInTheDocument();
  });

  it('renders a critical alert', () => {
    const alerts: DashboardAlert[] = [
      { level: 'critical', domain: 'system', message: 'CPU usage critical: 97%' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText(/CPU usage critical: 97%/)).toBeInTheDocument();
    expect(screen.getAllByText(/critical/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders domain badge', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'inference', message: 'Success rate low' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText('inference')).toBeInTheDocument();
  });

  it('renders multiple alerts', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'system', message: 'CPU high' },
      { level: 'critical', domain: 'system', message: 'RAM critical' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText('CPU high')).toBeInTheDocument();
    expect(screen.getByText('RAM critical')).toBeInTheDocument();
  });

  it('has role=alert for accessibility', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'system', message: 'Test alert' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders the correct icon for critical', () => {
    const alerts: DashboardAlert[] = [
      { level: 'critical', domain: 'disk', message: 'Disk full' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText('🔴')).toBeInTheDocument();
  });

  it('renders the correct icon for warning', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'disk', message: 'Disk getting full' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByText('🟡')).toBeInTheDocument();
  });

  it('renders data-testid alerts-banner', () => {
    const alerts: DashboardAlert[] = [
      { level: 'warning', domain: 'system', message: 'test' },
    ];
    render(<AlertsBanner alerts={alerts} />);
    expect(screen.getByTestId('alerts-banner')).toBeInTheDocument();
  });
});
