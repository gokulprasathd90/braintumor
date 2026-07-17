/**
 * InferenceMetricsPanel — prediction counts, latency stats, confidence
 * distribution bar chart, class distribution, and recent predictions table.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import type { InferenceMetrics } from '@/types';

const CLASS_COLORS: Record<string, string> = {
  glioma:     '#ef4444',
  meningioma: '#f59e0b',
  pituitary:  '#a855f7',
  notumor:    '#22c55e',
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-pipeline-50 rounded-xl px-4 py-3 border border-pipeline-100 text-center">
      <p className="text-xs text-pipeline-400 mb-1">{label}</p>
      <p className="text-xl font-bold text-pipeline-800">{value}</p>
      {sub && <p className="text-xs text-pipeline-400 mt-0.5">{sub}</p>}
    </div>
  );
}

interface Props {
  data: InferenceMetrics;
}

export default function InferenceMetricsPanel({ data }: Props) {
  // Confidence histogram data
  const histData = data.confidence_distribution.buckets.map((label, i) => ({
    bucket: label,
    count: data.confidence_distribution.counts[i] ?? 0,
  }));

  // Class distribution pie data
  const pieData = Object.entries(data.class_distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6" data-testid="inference-metrics-panel">
      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Total Predictions"
          value={String(data.total_predictions)}
          sub={`${data.batch_runs} batch run${data.batch_runs !== 1 ? 's' : ''}`}
        />
        <StatCard
          label="Success Rate"
          value={`${(data.success_rate * 100).toFixed(1)}%`}
          sub={`${data.succeeded} ok / ${data.failed} fail`}
        />
        <StatCard
          label="Avg Latency"
          value={data.avg_latency_ms !== null ? `${data.avg_latency_ms.toFixed(1)} ms` : '—'}
          sub={data.p95_latency_ms !== null ? `p95: ${data.p95_latency_ms.toFixed(1)} ms` : undefined}
        />
        <StatCard
          label="Batch Images"
          value={String(data.batch_images_processed)}
          sub={`${data.batch_succeeded} ok / ${data.batch_failed} fail`}
        />
      </div>

      {/* Confidence distribution */}
      {data.total_predictions > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-3">
            Confidence Distribution
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={histData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="bucket" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
                formatter={(v: number) => [v, 'Predictions']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Class distribution */}
      {pieData.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-3">
            Class Distribution
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  innerRadius={30}
                  paddingAngle={2}
                >
                  {pieData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={CLASS_COLORS[entry.name] ?? '#94a3b8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
                  formatter={(v: number, name: string) => [v, name]}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 11 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Per-model counts */}
      {Object.keys(data.per_model_counts).length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Predictions by Model
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.per_model_counts).map(([model, count]) => (
              <span
                key={model}
                className="text-xs font-medium px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100"
              >
                {model}: <strong>{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent predictions */}
      {data.recent_predictions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Recent Predictions
          </p>
          <div className="overflow-x-auto rounded-xl border border-pipeline-100">
            <table className="w-full text-xs">
              <thead className="bg-pipeline-50">
                <tr>
                  {['Model', 'Class', 'Confidence', 'Latency', 'Status', 'Time'].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left font-semibold text-pipeline-500 uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-pipeline-50">
                {data.recent_predictions.slice(0, 10).map((p, i) => (
                  <tr key={i} className="hover:bg-pipeline-50/50">
                    <td className="px-3 py-2 font-mono text-pipeline-600">{p.model_name}</td>
                    <td className="px-3 py-2 text-pipeline-700 capitalize">
                      {p.predicted_class ?? '—'}
                    </td>
                    <td className="px-3 py-2 text-pipeline-600">
                      {p.confidence !== null ? `${(p.confidence * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-3 py-2 text-pipeline-600">{p.timing_ms.toFixed(1)} ms</td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-0.5 rounded-full font-medium ${
                          p.success
                            ? 'bg-green-50 text-green-700'
                            : 'bg-red-50 text-red-700'
                        }`}
                      >
                        {p.success ? 'ok' : 'fail'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-pipeline-400 font-mono">
                      {new Date(p.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
