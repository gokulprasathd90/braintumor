import { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import Button from './Button';

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB
const ACCEPTED = { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] };

/**
 * UploadPanel — drag-and-drop MRI image uploader.
 *
 * Props:
 *  onUpload(file, onProgress) — called when user confirms; receives the File
 *    and a progress callback fn(percent: number).
 *    Should return a Promise that resolves on success or rejects with an Error.
 *  isLoading {boolean} — disables interaction during upload
 *  autoSubmit {boolean} — call onUpload immediately on file selection (no button click needed)
 */
export default function UploadPanel({ onUpload, isLoading = false, autoSubmit = false }) {
  const [file, setFile]         = useState(null);
  const [preview, setPreview]   = useState(null);
  const [dropError, setDropError] = useState('');
  const [progress, setProgress] = useState(0);       // 0–100
  const [uploading, setUploading] = useState(false);
  const prevPreview = useRef(null);

  // ── Dropzone ──────────────────────────────────────────────────────────────
  const onDrop = useCallback((accepted, rejected) => {
    setDropError('');
    setProgress(0);

    if (rejected.length > 0) {
      const err = rejected[0].errors[0];
      if (err.code === 'file-too-large')
        setDropError('File exceeds the 10 MB limit. Please choose a smaller image.');
      else if (err.code === 'file-invalid-type')
        setDropError('Invalid file type. Only JPEG and PNG MRI images are accepted.');
      else
        setDropError(err.message);
      clearPreview();
      return;
    }

    const selected = accepted[0];
    // Revoke previous object URL to avoid memory leaks
    if (prevPreview.current) URL.revokeObjectURL(prevPreview.current);
    const url = URL.createObjectURL(selected);
    prevPreview.current = url;

    setFile(selected);
    setPreview(url);

    // Auto-submit: call onUpload immediately without needing the button click
    if (autoSubmit && onUpload) {
      setUploading(true);
      setProgress(0);
      onUpload(selected, (percent) => setProgress(percent))
        .then(() => setProgress(100))
        .catch(() => setProgress(0))
        .finally(() => setUploading(false));
    }
  }, [autoSubmit, onUpload]); // eslint-disable-line react-hooks/exhaustive-deps

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: MAX_SIZE,
    multiple: false,
    disabled: isLoading || uploading,
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  const clearPreview = () => {
    if (prevPreview.current) {
      URL.revokeObjectURL(prevPreview.current);
      prevPreview.current = null;
    }
    setFile(null);
    setPreview(null);
  };

  const handleClear = () => {
    clearPreview();
    setDropError('');
    setProgress(0);
  };

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!file || !onUpload) return;

    setUploading(true);
    setProgress(0);

    try {
      await onUpload(file, (percent) => setProgress(percent));
      // Progress bar stays at 100 briefly; parent controls what happens next
      setProgress(100);
    } catch {
      // Parent handles error toasts — just reset progress
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const busy = isLoading || uploading;

  // ── Drop zone border colour ───────────────────────────────────────────────
  const borderClass = isDragActive
    ? 'border-blue-400 bg-blue-50'
    : dropError
      ? 'border-red-300 bg-red-50'
      : preview
        ? 'border-blue-300 bg-blue-50/40'
        : 'border-pipeline-300 bg-pipeline-50 hover:border-blue-400 hover:bg-blue-50';

  return (
    <div className="space-y-4">

      {/* ── Drop zone ─────────────────────────────────────────────────────── */}
      <div
        {...getRootProps()}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed
          p-8 text-center cursor-pointer transition-colors duration-150
          ${borderClass}
          ${busy ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''}
        `}
      >
        <input {...getInputProps()} aria-label="Upload MRI via dropzone" />

        {preview ? (
          /* ── Preview state ─────────────────────────────────────────────── */
          <div className="flex flex-col items-center gap-3 w-full">
            <div className="relative">
              <img
                src={preview}
                alt="Selected MRI preview"
                className="w-44 h-44 object-cover rounded-xl shadow-md border-2 border-blue-200"
              />
              {/* Remove button overlaid on image */}
              {!busy && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleClear(); }}
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-red-500 text-white
                             flex items-center justify-center shadow hover:bg-red-600 transition-colors"
                  aria-label="Remove selected image"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            <div className="text-sm text-pipeline-700 space-y-0.5">
              <p className="font-semibold truncate max-w-xs">{file.name}</p>
              <p className="text-pipeline-400 text-xs">
                {(file.size / 1024).toFixed(1)} KB · {file.type}
              </p>
            </div>

            {!busy && (
              <p className="text-xs text-pipeline-400">Click or drop to replace image</p>
            )}
          </div>
        ) : (
          /* ── Idle / drag state ─────────────────────────────────────────── */
          <div className="flex flex-col items-center gap-3 text-pipeline-500">
            <svg
              className={`w-14 h-14 transition-colors duration-150 ${isDragActive ? 'text-blue-400' : 'text-pipeline-300'}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.4}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>

            {isDragActive ? (
              <p className="font-semibold text-blue-600 text-base">Drop your MRI image here</p>
            ) : (
              <>
                <p className="font-semibold text-pipeline-700 text-base">Drag &amp; drop your MRI image</p>
                <p className="text-sm text-pipeline-400">or click to browse your files</p>
              </>
            )}
            <p className="text-xs text-pipeline-400 bg-pipeline-100 px-3 py-1 rounded-full">
              JPEG · PNG &nbsp;·&nbsp; max 10 MB
            </p>
          </div>
        )}
      </div>

      {/* ── Validation error ──────────────────────────────────────────────── */}
      {dropError && (
        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5" role="alert">
          <svg className="w-4 h-4 flex-shrink-0 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span className="font-medium">{dropError}</span>
        </div>
      )}

      {/* ── Upload progress bar ───────────────────────────────────────────── */}
      {uploading && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-medium text-pipeline-600">
            <span>Uploading…</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-pipeline-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-150"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
      )}

      {/* ── Action buttons ────────────────────────────────────────────────── */}
      {file && !dropError && (
        <div className="flex gap-3">
          <Button
            variant="primary"
            loading={busy}
            disabled={busy}
            onClick={handleSubmit}
            className="flex-1"
          >
            {uploading ? `Uploading… ${progress}%` : 'Upload & Detect'}
          </Button>
          <Button
            variant="secondary"
            onClick={handleClear}
            disabled={busy}
          >
            Remove
          </Button>
        </div>
      )}
    </div>
  );
}
