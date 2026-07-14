/**
 * MetricsHistoryChart — time-series line chart for rolling metric history.
 * Renders configurable metrics from the /dashboard/history endpoint.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { DashboardHistoryPoint } from '@/types';

export interface MetricLine {
  key: string;
  label: string;
  color: string;
  /** Format function for tooltip values, e.g. (v) => `${v}%`. */
  format?: (v: number) => string;
}

interface Props {
  data: DashboardHistoryPoint[];
  metrics: MetricLine[];
  height?: number;
  title?: string;
  emptyMessage?: string;
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts;
  }
}

export default function MetricsHistoryChart({
  data,
  metrics,
  height = 240,
  title,
  emptyMessage = 'No history data yet. Metrics are collected as the service runs.',
}: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-pipeline-400 italic" data-testid="metrics-history-chart-empty">
        {emptyMessage}
      </div>
    );
  }

  // Thin out to at most 120 points so the chart stays readable
  const MAX_POINTS = 120;
  const step = Math.max(1, Math.ceil(data.length / MAX_POINTS));
  const chartData = data
    .filter((_, i) => i % step === 0)
    .map((point) => ({
      ...point,
      _time: formatTimestamp(point.timestamp as string),
    }));

  return (
    <div data-testid="metrics-history-chart">
      {title && (
        <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-3">
          {title}
        </p>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="_time"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
            formatter={(value: number, name: string) => {
              const metric = metrics.find((m) => m.key === name || m.label === name);
              const formatted = metric?.format ? metric.format(value) : String(value);
              return [formatted, metric?.label ?? name];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value) => {
              const m = metrics.find((m) => m.key === value);
              return m?.label ?? value;
            }}
          />
          {metrics.map((m) => (
            <Line
              key={m.key}
              type="monotone"
              dataKey={m.key}
              name={m.key}
              stroke={m.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
