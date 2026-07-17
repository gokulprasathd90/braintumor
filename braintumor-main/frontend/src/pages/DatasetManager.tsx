/**
 * DatasetManager — view dataset info, validate raw data, and trigger a split.
 */

import Layout from '@/components/Layout';
import DatasetSummary from '@/components/DatasetSummary';
import LoadingSpinner from '@/components/LoadingSpinner';
import Button from '@/components/Button';
import { ToastContainer, useToast } from '@/components/Toast';
import { useDataset } from '@/hooks/useDataset';
import { useState } from 'react';

export default function DatasetManager() {
  const { info, validation, loading, validating, preparing, error, refresh, validate, prepare } = useDataset();
  const { toasts, addToast, dismissToast } = useToast();

  const [trainRatio, setTrainRatio] = useState(0.7);
  const [valRatio, setValRatio] = useState(0.15);
  const [overwrite, setOverwrite] = useState(false);

  const testRatio = parseFloat((1 - trainRatio - valRatio).toFixed(4));
  const ratioOk = Math.abs(trainRatio + valRatio + testRatio - 1.0) < 0.001;

  const handleValidate = async () => {
    const r = await validate();
    if (r) addToast(r.is_valid ? 'success' : 'warning', r.is_valid ? 'Dataset is valid' : `${r.errors.length} error(s) found`);
    else addToast('error', error?.detail ?? 'Validation failed');
  };

  const handlePrepare = async () => {
    const d = await prepare({ train_ratio: trainRatio, val_ratio: valRatio, test_ratio: testRatio, overwrite });
    if (d) addToast('success', 'Dataset prepared successfully');
    else addToast('error', error?.detail ?? 'Preparation failed');
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-pipeline-900">Dataset Manager</h1>
            <p className="text-pipeline-500 mt-1 text-sm">Validate, split, and inspect the dataset.</p>
          </div>
          <Button variant="secondary" onClick={refresh} loading={loading}>Refresh</Button>
        </div>

        {/* Dataset info */}
        <div className="card">
          <h2 className="section-title">Current Dataset</h2>
          {loading && <LoadingSpinner variant="card" message="Loading dataset info…" />}
          {!loading && info && <DatasetSummary info={info} />}
          {!loading && !info && (
            <div className="text-center py-8 text-pipeline-400">
              <p className="text-sm">No prepared dataset found.</p>
              <p className="text-xs mt-1">Run &ldquo;Prepare Dataset&rdquo; below to create a split.</p>
            </div>
          )}
        </div>

        {/* Validate */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="section-title mb-0">Validate Raw Dataset</h2>
            <Button variant="secondary" onClick={handleValidate} loading={validating}>Run Validation</Button>
          </div>
          {validation && (
            <div className={`rounded-xl px-4 py-3 border text-sm ${validation.is_valid ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
              <p className="font-semibold">{validation.is_valid ? '✓ Dataset is valid' : '✗ Validation failed'}</p>
              <p className="mt-1">Classes: {validation.classes_found.join(', ')} · Total images: {validation.total_images}</p>
              {validation.errors.map((e, i) => <p key={i} className="mt-0.5 text-xs">• {e}</p>)}
            </div>
          )}
        </div>

        {/* Prepare */}
        <div className="card space-y-4">
          <h2 className="section-title">Prepare Dataset</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Train Ratio', value: trainRatio, set: setTrainRatio },
              { label: 'Val Ratio',   value: valRatio,   set: setValRatio },
            ].map(({ label, value, set }) => (
              <div key={label} className="space-y-1.5">
                <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">{label}</label>
                <input type="number" min={0.05} max={0.9} step={0.05} value={value}
                  onChange={(e) => set(parseFloat(e.target.value))}
                  className="w-full rounded-lg border border-pipeline-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            ))}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">Test Ratio (auto)</label>
              <div className={`rounded-lg border px-3 py-2 text-sm font-mono ${ratioOk ? 'bg-pipeline-50 border-pipeline-200 text-pipeline-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                {testRatio.toFixed(2)}
              </div>
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} className="w-4 h-4 rounded text-blue-600" />
            <span className="text-sm text-pipeline-700">Overwrite existing split</span>
          </label>
          {error && <p className="text-sm text-red-600">{error.detail}</p>}
          <Button variant="primary" onClick={handlePrepare} loading={preparing} disabled={!ratioOk} className="w-full">
            Prepare Dataset
          </Button>
        </div>
      </div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </Layout>
  );
}
