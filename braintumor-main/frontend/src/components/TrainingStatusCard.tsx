/**
 * TrainingStatusCard — shows training job status, live polling indicator,
 * and result metrics when completed.
 */

import type { TrainingJob } from '@/types';

const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  queued:      { bg: 'bg-amber-50',  text: 'text-amber-700',  dot: 'bg-amber-400 animate-pulse', label: 'Queued' },
  running:     { bg: 'bg-blue-50',   text: 'text-blue-700',   dot: 'bg-blue-500 animate-pulse',  label: 'Running' },
  completed:   { bg: 'bg-green-50',  text: 'text-green-700',  dot: 'bg-green-500',               label: 'Completed' },
  failed:      { bg: 'bg-red-50',    text: 'text-red-700',    dot: 'bg-red-500',                 label: 'Failed' },
  interrupted: { bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-400',              label: 'Interrupted' },
  created:     { bg: 'bg-pipeline-50', text: 'text-pipeline-600', dot: 'bg-pipeline-400', label: 'Created' },
};

interface Props {
  job: TrainingJob;
  polling?: boolean;
}

export default function TrainingStatusCard({ job, polling = false }: Props) {
  const s = STATUS_STYLES[job.status] ?? STATUS_STYLES.created;

  const result = job.result as Record<string, unknown> | null;
  const accuracy = result?.final_val_accuracy as number | undefined;
  const duration = result?.training_duration_s as number | undefined;
  const epochs = result?.epochs_trained as number | undefined;

  const formatDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleTimeString() : '—';

  return (
    <div className={`card ${s.bg} space-y-4`} data-testid="training-status-card">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${s.dot}`} />
          <span className={`text-sm font-semibold ${s.text}`}>{s.label}</span>
          {polling && job.status === 'running' && (
            <span className="text-xs text-blue-500 animate-pulse">● polling</span>
          )}
        </div>
        <span className="text-xs font-mono text-pipeline-400 truncate max-w-[180px]" title={job.job_id}>
          {job.job_id.slice(0, 16)}…
        </span>
      </div>

      {/* Experiment ID */}
      {job.experiment_id && (
        <div className="text-xs text-pipeline-500">
          Experiment: <span className="font-mono text-pipeline-700">{job.experiment_id}</span>
        </div>
      )}

      {/* Timestamps */}
      <div className="grid grid-cols-3 gap-3 text-xs">
        {[
          { label: 'Created',  value: formatDate(job.created_at) },
          { label: 'Started',  value: formatDate(job.started_at) },
          { label: 'Finished', value: formatDate(job.finished_at) },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white/60 rounded-lg px-2 py-1.5 border border-white">
            <p className="text-pipeline-400">{label}</p>
            <p className="font-medium text-pipeline-700">{value}</p>
          </div>
        ))}
      </div>

      {/* Results (completed) */}
      {job.status === 'completed' && result && (
        <div className="grid grid-cols-3 gap-3 text-xs pt-1 border-t border-white/60">
          {accuracy !== undefined && (
            <div className="bg-white/60 rounded-lg px-2 py-2 text-center border border-white">
              <p className="text-pipeline-400">Val Accuracy</p>
              <p className="text-lg font-bold text-green-700">{(accuracy * 100).toFixed(2)}%</p>
            </div>
          )}
          {epochs !== undefined && (
            <div className="bg-white/60 rounded-lg px-2 py-2 text-center border border-white">
              <p className="text-pipeline-400">Epochs</p>
              <p className="text-lg font-bold text-pipeline-700">{epochs}</p>
            </div>
          )}
          {duration !== undefined && (
            <div className="bg-white/60 rounded-lg px-2 py-2 text-center border border-white">
              <p className="text-pipeline-400">Duration</p>
              <p className="text-lg font-bold text-pipeline-700">{(duration / 60).toFixed(1)} min</p>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {job.error && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <span className="font-semibold">Error: </span>{job.error}
        </div>
      )}
    </div>
  );
}
