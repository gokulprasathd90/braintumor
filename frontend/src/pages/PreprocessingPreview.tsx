/**
 * PreprocessingPreview — upload an image, run quality check and preview.
 */

import { useState } from 'react';
import Layout from '@/components/Layout';
import UploadPanel from '@/components/UploadPanel';
import QualityCheckPanel from '@/components/QualityCheckPanel';
import LoadingSpinner from '@/components/LoadingSpinner';
import Button from '@/components/Button';
import { ToastContainer, useToast } from '@/components/Toast';
import { usePreprocessing } from '@/hooks/usePreprocessing';

export default function PreprocessingPreview() {
  const { preview, report, previewData, loading, error, reset } = usePreprocessing();
  const { toasts, addToast, dismissToast } = useToast();
  const [includeAugmented, setIncludeAugmented] = useState(true);
  const [nAugmented, setNAugmented] = useState(4);
  const [activeAugIndex, setActiveAugIndex] = useState(0);

  const handleUpload = async (file: File) => {
    const res = await preview(file, { includeAugmented, nAugmented });
    if (res) addToast('success', 'Preview generated');
    else addToast('error', error?.detail ?? 'Preview failed');
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-pipeline-900">Preprocessing Preview</h1>
          <p className="text-pipeline-500 mt-1 text-sm">Upload an MRI image to inspect quality and preview augmentation variants.</p>
        </div>

        {/* Options */}
        {!previewData && (
          <div className="card">
            <h2 className="section-title">Options</h2>
            <div className="flex flex-wrap gap-4 items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={includeAugmented} onChange={(e) => setIncludeAugmented(e.target.checked)} className="w-4 h-4 rounded text-blue-600" />
                <span className="text-sm text-pipeline-700">Include augmentation variants</span>
              </label>
              {includeAugmented && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">Variants</label>
                  <input type="number" min={1} max={12} value={nAugmented} onChange={(e) => setNAugmented(Number(e.target.value))}
                    className="w-20 rounded-lg border border-pipeline-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Upload */}
        {!previewData && !loading && (
          <div className="card">
            <h2 className="section-title">Upload Image</h2>
            {/* Hidden direct input for programmatic/test access */}
            <input
              type="file"
              accept="image/jpeg,image/png"
              aria-label="Upload MRI image"
              className="sr-only"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
            />
            <UploadPanel onUpload={handleUpload} isLoading={loading} autoSubmit />
          </div>
        )}

        {loading && <div className="card"><LoadingSpinner variant="card" message="Generating preview…" /></div>}
        {error && !loading && (
          <div className="card bg-red-50 border-red-200 text-sm text-red-700">
            {error.detail}
            <button onClick={reset} className="ml-3 underline">Reset</button>
          </div>
        )}

        {/* Results */}
        {previewData && !loading && (
          <div className="space-y-4">
            {/* Quality report */}
            <div className="card">
              <h2 className="section-title">Quality Report</h2>
              {report && <QualityCheckPanel report={report} />}
            </div>

            {/* Preprocessed image */}
            <div className="card">
              <h2 className="section-title">Preprocessed Image</h2>
              <div className="flex justify-center">
                <img src={`data:image/png;base64,${previewData.preprocessed_b64}`}
                  alt="Preprocessed MRI" className="max-h-64 rounded-xl border border-pipeline-200 shadow" />
              </div>
            </div>

            {/* Augmentation variants */}
            {previewData.augmented_b64.length > 0 && (
              <div className="card">
                <h2 className="section-title">Augmentation Variants ({previewData.augmented_b64.length})</h2>
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {previewData.augmented_b64.map((b64, i) => (
                    <button key={i} onClick={() => setActiveAugIndex(i)}
                      className={`flex-shrink-0 rounded-lg overflow-hidden border-2 transition-all ${activeAugIndex === i ? 'border-blue-500' : 'border-transparent'}`}>
                      <img src={`data:image/png;base64,${b64}`} alt={`Variant ${i + 1}`} className="w-20 h-20 object-cover" />
                    </button>
                  ))}
                </div>
                <div className="mt-3 flex justify-center">
                  <img src={`data:image/png;base64,${previewData.augmented_b64[activeAugIndex]}`}
                    alt={`Augmentation variant ${activeAugIndex + 1}`} className="max-h-56 rounded-xl border border-blue-200 shadow" />
                </div>
              </div>
            )}

            <button onClick={reset}
              className="w-full py-2 text-sm text-pipeline-500 border border-pipeline-200 rounded-xl hover:bg-pipeline-50 transition-colors">
              ← Preview Another Image
            </button>
          </div>
        )}
      </div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </Layout>
  );
}
