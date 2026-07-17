/**
 * Training — launch a training job and watch live status updates.
 */

import { useState } from 'react';
import Layout from '@/components/Layout';
import TrainingStatusCard from '@/components/TrainingStatusCard';
import ModelSelector from '@/components/ModelSelector';
import Button from '@/components/Button';
import { ToastContainer, useToast } from '@/components/Toast';
import { useTraining } from '@/hooks/useTraining';
import type { ArchitectureName, TrainingStartRequest } from '@/types';

const DEFAULTS: TrainingStartRequest = {
  architecture: 'efficientnet',
  epochs: 30,
  batch_size: 32,
  learning_rate: 0.0001,
  fine_tune: true,
  fine_tune_layers: 20,
  fine_tune_epochs: 10,
  seed: 42,
};

export default function Training() {
  const { start, job, loading, polling, error, reset } = useTraining();
  const { toasts, addToast, dismissToast } = useToast();
  const [config, setConfig] = useState<TrainingStartRequest>(DEFAULTS);

  const handleStart = async () => {
    const res = await start(config);
    if (res) addToast('success', `Job ${res.job_id.slice(0, 8)} started`);
    else addToast('error', error?.detail ?? 'Failed to start training');
  };

  const set = (k: keyof TrainingStartRequest, v: unknown) =>
    setConfig((c) => ({ ...c, [k]: v }));

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-pipeline-900">Train a Model</h1>
          <p className="text-pipeline-500 mt-1 text-sm">Configure and launch an async training job.</p>
        </div>

        {/* Config form */}
        {!job && (
          <div className="card space-y-5">
            <h2 className="section-title">Training Configuration</h2>

            <ModelSelector
              value={config.architecture as ArchitectureName}
              onChange={(v) => set('architecture', v)}
              label="Architecture"
            />

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {[
                { key: 'epochs', label: 'Epochs', min: 1, max: 500 },
                { key: 'batch_size', label: 'Batch Size', min: 1, max: 256 },
              ].map(({ key, label, min, max }) => (
                <div key={key} className="space-y-1.5">
                  <label htmlFor={`training-${key}`} className="block text-xs font-semibold text-pipeline-600 uppercase tracking-wide">{label}</label>
                  <input id={`training-${key}`} type="number" min={min} max={max}
                    value={config[key as keyof TrainingStartRequest] as number}
                    onChange={(e) => set(key as keyof TrainingStartRequest, Number(e.target.value))}
                    className="w-full rounded-lg border border-pipeline-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
              <div className="space-y-1.5">
                <label htmlFor="training-learning_rate" className="block text-xs font-semibold text-pipeline-600 uppercase tracking-wide">Learning Rate</label>
                <input id="training-learning_rate" type="number" step="0.00001" min="0.000001" max="0.1"
                  value={config.learning_rate}
                  onChange={(e) => set('learning_rate', parseFloat(e.target.value))}
                  className="w-full rounded-lg border border-pipeline-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Fine-tuning toggle */}
            <div className="space-y-3 p-4 bg-pipeline-50 rounded-xl border border-pipeline-100">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={config.fine_tune} onChange={(e) => set('fine_tune', e.target.checked)}
                  className="w-4 h-4 rounded text-blue-600" />
                <span className="text-sm font-medium text-pipeline-700">Enable Phase-2 Fine-tuning</span>
              </label>
              {config.fine_tune && (
                <div className="grid grid-cols-2 gap-4 pt-1">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-pipeline-500 uppercase">Unfreeze Layers</label>
                    <input type="number" min={1} max={200} value={config.fine_tune_layers}
                      onChange={(e) => set('fine_tune_layers', Number(e.target.value))}
                      className="w-full rounded-lg border border-pipeline-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-pipeline-500 uppercase">Fine-tune Epochs</label>
                    <input type="number" min={1} max={200} value={config.fine_tune_epochs}
                      onChange={(e) => set('fine_tune_epochs', Number(e.target.value))}
                      className="w-full rounded-lg border border-pipeline-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                </div>
              )}
            </div>

            <Button variant="primary" onClick={handleStart} loading={loading} className="w-full">
              Start Training Job
            </Button>
          </div>
        )}

        {/* Live status */}
        {job && (
          <div className="space-y-4">
            <TrainingStatusCard job={job} polling={polling} />
            {(job.status === 'completed' || job.status === 'failed') && (
              <button onClick={reset}
                className="w-full py-2 text-sm text-pipeline-500 hover:text-pipeline-800 border border-pipeline-200 rounded-xl hover:bg-pipeline-50 transition-colors">
                ← New Training Job
              </button>
            )}
          </div>
        )}

        {error && !job && (
          <div className="card bg-red-50 border-red-200">
            <p className="text-sm text-red-700">{error.detail}</p>
          </div>
        )}
      </div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </Layout>
  );
}
