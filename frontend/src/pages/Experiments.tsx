/**
 * Experiments — browse past training runs, filter by architecture/status,
 * and inspect a selected experiment's metrics.
 */

import { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import ExperimentList from '@/components/ExperimentList';
import LoadingSpinner from '@/components/LoadingSpinner';
import { listExperiments, getExperiment } from '@/api/training';
import type { Experiment } from '@/types';

const ARCH_OPTIONS = ['', 'cnn', 'vgg16', 'resnet50', 'efficientnet'];
const STATUS_OPTIONS = ['', 'completed', 'running', 'failed', 'queued'];

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selected, setSelected] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [arch, setArch] = useState('');
  const [status, setStatus] = useState('');

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await listExperiments({ architecture: arch || undefined, status: status || undefined, limit: 100 });
      setExperiments(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchList(); }, [arch, status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = async (exp: Experiment) => {
    setDetailLoading(true);
    setSelected(null);
    try {
      const full = await getExperiment(exp.experiment_id);
      setSelected(full);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-pipeline-900">Experiments</h1>
          <p className="text-pipeline-500 mt-1 text-sm">Browse and inspect all past training runs.</p>
        </div>

        {/* Filters */}
        <div className="card flex flex-wrap gap-4 items-end">
          {[
            { label: 'Architecture', options: ARCH_OPTIONS, value: arch, set: setArch },
            { label: 'Status', options: STATUS_OPTIONS, value: status, set: setStatus },
          ].map(({ label, options, value, set }) => (
            <div key={label} className="space-y-1.5 min-w-[140px]">
              <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">{label}</label>
              <select value={value} onChange={(e) => set(e.target.value)}
                className="rounded-lg border border-pipeline-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full">
                {options.map((o) => <option key={o} value={o}>{o || `All ${label}s`}</option>)}
              </select>
            </div>
          ))}
          <button onClick={fetchList} className="text-sm font-medium text-blue-600 border border-blue-200 rounded-lg px-4 py-2 hover:bg-blue-50 transition-colors">
            Refresh
          </button>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* List */}
          <div className="lg:col-span-2">
            <ExperimentList experiments={experiments} onSelect={handleSelect} selectedId={selected?.experiment_id} loading={loading} />
          </div>

          {/* Detail pane */}
          <div className="space-y-4">
            {detailLoading && <div className="card"><LoadingSpinner variant="card" message="Loading…" /></div>}
            {selected && !detailLoading && (
              <div className="card space-y-4">
                <h2 className="section-title">Experiment Detail</h2>
                <div className="space-y-2 text-xs">
                  {[
                    ['ID', selected.experiment_id.slice(-20)],
                    ['Architecture', selected.architecture],
                    ['Status', selected.status],
                    ['Val Accuracy', selected.best_val_accuracy != null ? `${(selected.best_val_accuracy * 100).toFixed(2)}%` : '—'],
                    ['Epochs', String(selected.epochs_trained ?? '—')],
                    ['Duration', selected.duration_s != null ? `${(selected.duration_s / 60).toFixed(1)} min` : '—'],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2 py-1.5 border-b border-pipeline-50">
                      <span className="text-pipeline-400 font-medium">{k}</span>
                      <span className="text-pipeline-700 font-semibold text-right">{v}</span>
                    </div>
                  ))}
                </div>

                {/* Evaluation metrics */}
                {selected.evaluation && (
                  <div>
                    <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">Evaluation</p>
                    <div className="grid grid-cols-2 gap-2">
                      {(['accuracy', 'f1', 'precision', 'recall', 'auc_roc'] as const).map((k) => {
                        const v = (selected.evaluation as Record<string, number>)[k];
                        return v != null ? (
                          <div key={k} className="bg-pipeline-50 rounded-lg px-2 py-1.5 text-center border border-pipeline-100">
                            <p className="text-pipeline-400 text-xs capitalize">{k.replace('_', ' ')}</p>
                            <p className="font-bold text-pipeline-700">{(v * 100).toFixed(2)}%</p>
                          </div>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
            {!selected && !detailLoading && (
              <div className="card text-center py-10 text-pipeline-400 text-sm">
                Click an experiment to inspect it
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
