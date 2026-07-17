/**
 * src/components/SystemHealthPanel.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SystemHealthPanel from './SystemHealthPanel';
import type { SystemMetrics } from '@/types';

const BASE_DATA: SystemMetrics = {
  timestamp: '2024-07-14T12:00:00Z',
  uptime_seconds: 3612,
  platform: 'Linux',
  python_version: '3.11.0',
  cpu_percent: 34.1, cpu_per_core: [28.0, 40.2, 35.0, 42.0],
  cpu_count_logical: 4, cpu_count_physical: 2, cpu_freq_mhz: 2400,
  ram_total_mb: 8192, ram_used_mb: 4201, ram_available_mb: 3991, ram_percent: 51.3,
  disk_total_gb: 256, disk_used_gb: 109.3, disk_free_gb: 146.7, disk_percent: 42.7,
  gpu_available: false, gpu_count: 0, gpus: [],
  process_pid: 1234, process_cpu_percent: 2.1, process_ram_mb: 412.8, process_threads: 8,
};

describe('SystemHealthPanel', () => {
  it('renders the panel with testid', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByTestId('system-health-panel')).toBeInTheDocument();
  });

  it('renders four MetricGauge components (CPU, RAM, Disk, GPU/none)', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    const gauges = screen.getAllByTestId('metric-gauge');
    expect(gauges.length).toBe(3); // CPU, RAM, Disk (no GPU row when unavailable)
  });

  it('shows platform info', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByText('Linux')).toBeInTheDocument();
  });

  it('shows python version', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByText('3.11.0')).toBeInTheDocument();
  });

  it('shows uptime formatted', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    // 3612 seconds = 1h 0m
    expect(screen.getByText(/1h 0m/)).toBeInTheDocument();
  });

  it('shows process PID', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByText('1234')).toBeInTheDocument();
  });

  it('shows process RAM', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    // toFixed(0) rounds 412.8 to 413
    expect(screen.getByText(/41[23] MB/)).toBeInTheDocument();
  });

  it('shows No GPU when unavailable', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByText(/No GPU/)).toBeInTheDocument();
  });

  it('shows GPU gauge when available', () => {
    const withGpu: SystemMetrics = {
      ...BASE_DATA,
      gpu_available: true,
      gpu_count: 1,
      gpus: [{ index: 0, name: 'NVIDIA RTX 4090', memory_used_mb: 2048, memory_total_mb: 24576, utilization_percent: 55 }],
    };
    render(<SystemHealthPanel data={withGpu} />);
    expect(screen.getByText('NVIDIA RTX 4090')).toBeInTheDocument();
  });

  it('renders per-core CPU bars', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    expect(screen.getByText('Per-Core CPU Usage')).toBeInTheDocument();
  });

  it('shows no per-core bars when array is empty', () => {
    render(<SystemHealthPanel data={{ ...BASE_DATA, cpu_per_core: [] }} />);
    expect(screen.queryByText('Per-Core CPU Usage')).not.toBeInTheDocument();
  });

  it('shows RAM in GB', () => {
    render(<SystemHealthPanel data={BASE_DATA} />);
    // 4201 MB / 1024 = 4.1 GB
    expect(screen.getByText(/4\.1 \/ 8\.0 GB/)).toBeInTheDocument();
  });
});
