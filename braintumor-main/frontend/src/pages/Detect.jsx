import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import UploadPanel from '../components/UploadPanel';
import PipelineVisualizer from '../components/PipelineVisualizer';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import { ToastContainer, useToast } from '../components/Toast';
import { uploadImage, preprocessImage } from '../services/api';

export default function Detect() {
  const navigate = useNavigate();
  const { toasts, addToast, dismissToast } = useToast();

  const [isLoading,        setIsLoading]        = useState(false);
  const [error,            setError]            = useState('');
  const [uploadedImage,    setUploadedImage]    = useState(null);
  // { image_id, filename, raw_path, upload_time }
  const [preprocessResult, setPreprocessResult] = useState(null);
  // { image_id, resized_url, enhanced_url, acea_stats, computational_time_ms }
  const [activeStep,       setActiveStep]       = useState(null);
  const [completedSteps,   setCompletedSteps]   = useState(new Set());

  const markDone = (step) =>
    setCompletedSteps((prev) => new Set([...prev, step]));

  // ── Upload handler ────────────────────────────────────────────────────────
  const handleUpload = async (file, onProgress) => {
    setError('');
    setUploadedImage(null);
    setPreprocessResult(null);
    setCompletedSteps(new Set());
    setActiveStep('upload');
    setIsLoading(true);

    try {
      const res  = await uploadImage(file, (event) => {
        if (event.total) {
          const pct = Math.round((event.loaded / event.total) * 100);
          onProgress(pct);
        }
      });
      const data = res?.data ?? res;

      markDone('upload');
      setUploadedImage(data);
      addToast('success', `"${data.filename}" uploaded successfully.`);
    } catch (err) {
      setActiveStep(null);
      const msg = err.message || 'Upload failed. Please try again.';
      setError(msg);
      addToast('error', msg);
      throw err;   // UploadPanel resets its progress bar
    } finally {
      setIsLoading(false);
      setActiveStep(null);
    }
  };

  // ── Auto-run preprocess once upload completes ─────────────────────────────
  useEffect(() => {
    if (!uploadedImage) return;
    handlePreprocess(uploadedImage.image_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedImage]);

  const handlePreprocess = async (imageId) => {
    setError('');
    setActiveStep('preprocess');
    setIsLoading(true);

    try {
      const res    = await preprocessImage(imageId);
      const data   = res?.data ?? res;

      markDone('preprocess');
      setPreprocessResult(data);
      addToast('success', 'ACEA contrast enhancement complete.');
    } catch (err) {
      const msg = err.message || 'Preprocessing failed. Please try again.';
      setError(msg);
      addToast('error', msg);
    } finally {
      setIsLoading(false);
      setActiveStep(null);
    }
  };

  // ── Reset everything ──────────────────────────────────────────────────────
  const handleReset = () => {
    setUploadedImage(null);
    setPreprocessResult(null);
    setError('');
    setActiveStep(null);
    setCompletedSteps(new Set());
  };

  // ── Derived display state ─────────────────────────────────────────────────
  const showUploadPanel   = !uploadedImage;
  const showSpinner       = isLoading;
  const showPreprocessed  = !!preprocessResult && !isLoading;

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-pipeline-900">Tumor Detection</h1>
          <p className="text-pipeline-500 mt-1 text-sm">
            Upload an MRI scan to run the detection pipeline.
          </p>
        </div>

        {/* Pipeline step tracker */}
        <div className="card">
          <h2 className="section-title">Pipeline Progress</h2>
          <PipelineVisualizer activeStep={activeStep} completedSteps={completedSteps} />
        </div>

        {/* Upload panel */}
        {showUploadPanel && (
          <div className="card">
            <h2 className="section-title">Upload MRI Image</h2>
            <UploadPanel onUpload={handleUpload} isLoading={isLoading} />
          </div>
        )}

        {/* Error message */}
        {error && (
          <ErrorMessage message={error} onRetry={handleReset} />
        )}

        {/* Processing spinner */}
        {showSpinner && uploadedImage && (
          <div className="card flex items-center gap-4 py-6">
            <LoadingSpinner size="md" message="" />
            <div>
              <p className="font-semibold text-pipeline-800">
                {activeStep === 'preprocess'
                  ? 'Running ACEA contrast enhancement…'
                  : 'Processing…'}
              </p>
              <p className="text-xs text-pipeline-400 mt-0.5">
                Resize → 256×256 · Adaptive contrast stretch (Eq. 1)
              </p>
            </div>
          </div>
        )}

        {/* ── Preprocessing result card ───────────────────────────────────── */}
        {showPreprocessed && (
          <div className="card space-y-5">

            {/* Section header */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24"
                     stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round"
                        d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-pipeline-900">Preprocessing complete</p>
                <p className="text-xs text-pipeline-400 mt-0.5">
                  Resize (256×256) · ACEA contrast enhancement · {preprocessResult.computational_time_ms.toFixed(0)} ms
                </p>
              </div>
            </div>

            {/* Side-by-side image comparison */}
            <div className="grid grid-cols-2 gap-4">

              {/* Original */}
              <div className="space-y-2">
                <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                  Original (resized)
                </p>
                <div className="rounded-lg overflow-hidden border border-pipeline-200 bg-black">
                  <img
                    src={`http://localhost:5000/processed${preprocessResult.resized_url}`}
                    alt="Resized MRI scan"
                    className="w-full h-44 object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div className="hidden h-44 items-center justify-center text-xs text-pipeline-400">
                    Image not available
                  </div>
                </div>
              </div>

              {/* ACEA enhanced */}
              <div className="space-y-2">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
                  ACEA Enhanced
                </p>
                <div className="rounded-lg overflow-hidden border border-blue-200 bg-black">
                  <img
                    src={`http://localhost:5000/processed${preprocessResult.enhanced_url}`}
                    alt="ACEA contrast-enhanced MRI"
                    className="w-full h-44 object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div className="hidden h-44 items-center justify-center text-xs text-pipeline-400">
                    Image not available
                  </div>
                </div>
              </div>
            </div>

            {/* ACEA stats */}
            {preprocessResult.acea_stats && (
              <div>
                <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
                  ACEA Parameters (Equation 1)
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: 'Pmin',  value: preprocessResult.acea_stats.Pmin },
                    { label: 'Pmax',  value: preprocessResult.acea_stats.Pmax },
                    { label: 'N_V',   value: preprocessResult.acea_stats.nV   },
                    { label: 'μT',    value: preprocessResult.acea_stats.muT  },
                    { label: 'μV',    value: preprocessResult.acea_stats.muV  },
                    {
                      label: 'Clipped',
                      value: `${((preprocessResult.acea_stats.clippedPixels /
                               preprocessResult.acea_stats.totalPixels) * 100).toFixed(1)}%`,
                    },
                  ].map(({ label, value }) => (
                    <div key={label}
                         className="bg-pipeline-50 rounded-lg px-3 py-2 text-center border border-pipeline-100">
                      <p className="text-xs text-pipeline-400">{label}</p>
                      <p className="text-sm font-semibold text-pipeline-800 font-mono">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Next-step notice */}
            <p className="text-xs text-pipeline-500 bg-pipeline-50 rounded-lg px-3 py-2 border border-pipeline-100">
              Next: Median Filter denoising → Fuzzy C-Means segmentation
              (not yet implemented — coming in the next phase).
            </p>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <Button
                variant="primary"
                className="flex-1"
                onClick={() => navigate(`/results?imageId=${preprocessResult.image_id}`)}
              >
                View Results Page
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24"
                     stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round"
                        d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Button>
              <Button variant="secondary" onClick={handleReset}>
                Upload Another
              </Button>
            </div>
          </div>
        )}

      </div>

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </Layout>
  );
}
