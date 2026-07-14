/**
 * TrainingMetricsPanel — job counts, architecture popularity bar chart,
 * best accuracy, and recent jobs/experiments tables.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { TrainingMetrics, RecentJob, RecentExperiment } from '@/types';

const STATUS_BADGE: Record<string, string> = {
  queued:      'bg-amber-50 text-amber-700 border-amber-200',
  running:     'bg-blue-50 text-blue-700 border-blue-200',
  completed:   'bg-green-50 text-green-700 border-green-200',
  failed:      'bg-red-50 text-red-700 border-red-200',
  interrupted: 'bg-orange-50 text-orange-700 border-orange-200',
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_BADGE[status] ?? 'bg-pipeline-100 text-pipeline-600 border-pipeline-200';
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {status}
    </span>
  );
}

function StatCard({ label, value, colour }: { label: string; value: string | number; colour?: string }) {
  return (
    <div className="bg-pipeline-50 rounded-xl px-4 py-3 border border-pipeline-100 text-center">
      <p className="text-xs text-pipeline-400 mb-1">{label}</p>
      <p className={`text-xl font-bold ${colour ?? 'text-pipeline-800'}`}>{value}</p>
    </div>
  );
}

function formatDuration(s: number | null): string {
  if (s === null) return '—';
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${(s / 60).toFixed(1)} min`;
}

interface Props {
  data: TrainingMetrics;
}

export default function TrainingMetricsPanel({ data }: Props) {
  const archData = Object.entries(data.architecture_counts).map(([name, count]) => ({
    name,
    count,
  }));

  return (
    <div className="space-y-6" data-testid="training-metrics-panel">
      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Total Jobs" value={data.total_jobs} />
        <StatCard label="Running" value={data.running_jobs} colour="text-blue-700" />
        <StatCard label="Completed" value={data.completed_jobs} colour="text-green-700" />
        <StatCard label="Failed" value={data.failed_jobs} colour="text-red-700" />
        <StatCard
          label="Best Val Acc"
          value={data.best_val_accuracy !== null ? `${(data.best_val_accuracy * 100).toFixed(2)}%` : '—'}
          colour="text-purple-700"
        />
      </div>

      {/* Architecture popularity */}
      {archData.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-3">
            Jobs by Architecture
          </p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={archData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
                formatter={(v: number) => [v, 'Jobs']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent jobs */}
      {data.recent_jobs.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Recent Jobs
          </p>
          <div className="overflow-x-auto rounded-xl border border-pipeline-100">
            <table className="w-full text-xs">
              <thead className="bg-pipeline-50">
                <tr>
                  {['Job ID', 'Architecture', 'Status', 'Duration', 'Started'].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-semibold text-pipeline-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-pipeline-50">
                {data.recent_jobs.map((job) => (
                  <tr key={job.job_id} className="hover:bg-pipeline-50/50">
                    <td className="px-3 py-2 font-mono text-pipeline-500" title={job.job_id}>
                      {job.job_id.slice(0, 12)}…
                    </td>
                    <td className="px-3 py-2 text-pipeline-700 capitalize">{job.architecture}</td>
                    <td className="px-3 py-2"><StatusBadge status={job.status} /></td>
                    <td className="px-3 py-2 text-pipeline-600">{formatDuration(job.duration_s)}</td>
                    <td className="px-3 py-2 text-pipeline-400 font-mono">
                      {job.started_at ? new Date(job.started_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent experiments */}
      {data.recent_experiments.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Recent Experiments
          </p>
          <div className="overflow-x-auto rounded-xl border border-pipeline-100">
            <table className="w-full text-xs">
              <thead className="bg-pipeline-50">
                <tr>
                  {['Experiment', 'Architecture', 'Val Acc', 'Epochs', 'Duration', 'Status'].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-semibold text-pipeline-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-pipeline-50">
                {data.recent_experiments.map((exp, i) => (
                  <tr key={exp.experiment_id ?? i} className="hover:bg-pipeline-50/50">
                    <td className="px-3 py-2 font-mono text-pipeline-500" title={exp.experiment_id ?? ''}>
                      {exp.experiment_id ? exp.experiment_id.slice(-16) : '—'}
                    </td>
                    <td className="px-3 py-2 text-pipeline-700 capitalize">{exp.architecture ?? '—'}</td>
                    <td className="px-3 py-2 font-semibold text-green-700">
                      {exp.best_val_accuracy !== null
                        ? `${(exp.best_val_accuracy * 100).toFixed(2)}%`
                        : '—'}
                    </td>
                    <td className="px-3 py-2 text-pipeline-600">{exp.epochs_trained ?? '—'}</td>
                    <td className="px-3 py-2 text-pipeline-600">{formatDuration(exp.duration_s)}</td>
                    <td className="px-3 py-2">
                      {exp.status && <StatusBadge status={exp.status} />}
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
