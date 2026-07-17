/**
 * ProbabilityChart — Recharts bar chart of per-class probabilities.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { PredictionResult } from '@/types';

const COLORS: Record<string, string> = {
  glioma:     '#ef4444',
  meningioma: '#f59e0b',
  pituitary:  '#a855f7',
  notumor:    '#22c55e',
};

interface Props {
  result: PredictionResult;
  height?: number;
}

export default function ProbabilityChart({ result, height = 220 }: Props) {
  const data = Object.entries(result.probabilities).map(([name, value]) => ({
    name,
    value: parseFloat((value * 100).toFixed(2)),
  }));

  return (
    <div data-testid="probability-chart">
      <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-3">
        Class Probabilities
      </p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Probability']}
            contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={COLORS[entry.name] ?? '#3b82f6'}
                opacity={entry.name === result.predicted_class ? 1 : 0.55}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
