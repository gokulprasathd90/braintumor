/**
 * ExperimentList — table of past training experiments with status badges
 * and links to detail view.
 */

import type { Experiment } from '@/types';

const STATUS_BADGE: Record<string, string> = {
  completed:   'bg-green-100 text-green-700',
  running:     'bg-blue-100 text-blue-700',
  failed:      'bg-red-100 text-red-700',
  queued:      'bg-amber-100 text-amber-700',
  interrupted: 'bg-orange-100 text-orange-700',
  created:     'bg-pipeline-100 text-pipeline-600',
};

interface Props {
  experiments: Experiment[];
  onSelect?: (exp: Experiment) => void;
  selectedId?: string;
  loading?: boolean;
}

export default function ExperimentList({ experiments, onSelect, selectedId, loading }: Props) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-12 rounded-xl bg-pipeline-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (experiments.length === 0) {
    return (
      <div className="text-center py-12 text-pipeline-400">
        <p className="font-medium">No experiments yet</p>
        <p className="text-sm mt-1">Start a training job to see results here.</p>
      </div>
    );
  }

  const fmtDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';

  return (
    <div className="overflow-x-auto rounded-xl border border-pipeline-200" data-testid="experiment-list">
      <table className="min-w-full text-sm">
        <thead className="bg-pipeline-50">
          <tr>
            {['Experiment', 'Architecture', 'Status', 'Val Acc', 'Epochs', 'Date'].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-pipeline-100 bg-white">
          {experiments.map((exp) => (
            <tr
              key={exp.experiment_id}
              onClick={() => onSelect?.(exp)}
              className={`hover:bg-pipeline-50 transition-colors ${onSelect ? 'cursor-pointer' : ''} ${selectedId === exp.experiment_id ? 'bg-blue-50' : ''}`}
            >
              <td className="px-4 py-3">
                <span className="font-mono text-xs text-pipeline-600 truncate block max-w-[160px]" title={exp.experiment_id}>
                  {exp.experiment_id.slice(-16)}
                </span>
              </td>
              <td className="px-4 py-3 text-pipeline-700 font-medium">{exp.architecture}</td>
              <td className="px-4 py-3">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_BADGE[exp.status] ?? STATUS_BADGE.created}`}>
                  {exp.status}
                </span>
              </td>
              <td className="px-4 py-3 text-pipeline-700">
                {exp.best_val_accuracy != null ? `${(exp.best_val_accuracy * 100).toFixed(2)}%` : '—'}
              </td>
              <td className="px-4 py-3 text-pipeline-500">{exp.epochs_trained ?? '—'}</td>
              <td className="px-4 py-3 text-pipeline-400 text-xs">{fmtDate(exp.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
