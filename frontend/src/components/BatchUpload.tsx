/**
 * BatchUpload — multi-file or ZIP drag-and-drop uploader.
 *
 * Props:
 *   mode          'files' | 'zip'
 *   onSubmit      called with (files, options) or (zipFile, options)
 *   loading       disable interactions during inference
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import Button from './Button';

export type BatchMode = 'files' | 'zip';

interface Props {
  mode: BatchMode;
  onSubmit: (payload: File | File[]) => void;
  loading?: boolean;
  modelName?: string;
}

const ACCEPT_IMAGES = { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] };
const ACCEPT_ZIP    = { 'application/zip': ['.zip'], 'application/x-zip-compressed': ['.zip'] };

export default function BatchUpload({ mode, onSubmit, loading = false }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [dropError, setDropError] = useState('');

  const onDrop = useCallback((accepted: File[], rejected: { errors: { code: string; message: string }[] }[]) => {
    setDropError('');
    if (rejected.length > 0) {
      setDropError(rejected[0].errors[0]?.message ?? 'Invalid file');
      return;
    }
    if (mode === 'zip') {
      setFiles(accepted.slice(0, 1));
    } else {
      setFiles((prev) => {
        const existing = new Set(prev.map((f) => f.name));
        return [...prev, ...accepted.filter((f) => !existing.has(f.name))];
      });
    }
  }, [mode]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: mode === 'zip' ? ACCEPT_ZIP : ACCEPT_IMAGES,
    multiple: mode === 'files',
    maxSize: 50 * 1024 * 1024,
    disabled: loading,
  });

  const removeFile = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleSubmit = () => {
    if (files.length === 0) return;
    onSubmit(mode === 'zip' ? files[0] : files);
  };

  const borderClass = isDragActive
    ? 'border-blue-400 bg-blue-50'
    : dropError
      ? 'border-red-300 bg-red-50'
      : files.length > 0
        ? 'border-blue-300 bg-blue-50/30'
        : 'border-pipeline-300 bg-pipeline-50 hover:border-blue-400 hover:bg-blue-50';

  return (
    <div className="space-y-4" data-testid="batch-upload">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center
          cursor-pointer transition-colors duration-150 ${borderClass} ${loading ? 'opacity-60 pointer-events-none' : ''}`}
      >
        <input {...getInputProps()} aria-label={mode === 'zip' ? 'Upload ZIP archive' : 'Upload MRI images'} />
        <svg className={`w-12 h-12 mb-3 transition-colors ${isDragActive ? 'text-blue-400' : 'text-pipeline-300'}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.4}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        {isDragActive ? (
          <p className="font-semibold text-blue-600">Drop here</p>
        ) : (
          <>
            <p className="font-semibold text-pipeline-700">
              {mode === 'zip' ? 'Drag & drop a ZIP archive' : 'Drag & drop MRI images'}
            </p>
            <p className="text-sm text-pipeline-400 mt-1">or click to browse</p>
            <p className="text-xs text-pipeline-400 mt-2 bg-pipeline-100 px-3 py-1 rounded-full">
              {mode === 'zip' ? 'ZIP file containing JPEG/PNG images' : 'JPEG · PNG · up to 50 MB total'}
            </p>
          </>
        )}
      </div>

      {dropError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2" role="alert">
          {dropError}
        </p>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
            {mode === 'zip' ? 'Archive' : `${files.length} image${files.length !== 1 ? 's' : ''} queued`}
          </p>
          <div className="max-h-48 overflow-y-auto space-y-1.5">
            {files.map((f) => (
              <div key={f.name} className="flex items-center justify-between bg-pipeline-50 rounded-lg px-3 py-2 border border-pipeline-100">
                <div className="flex items-center gap-2 min-w-0">
                  <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159" />
                  </svg>
                  <span className="text-xs text-pipeline-700 truncate">{f.name}</span>
                  <span className="text-xs text-pipeline-400 flex-shrink-0">({(f.size / 1024).toFixed(0)} KB)</span>
                </div>
                {!loading && (
                  <button onClick={() => removeFile(f.name)} className="text-pipeline-300 hover:text-red-500 ml-2" aria-label={`Remove ${f.name}`}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {files.length > 0 && (
        <div className="flex gap-3">
          <Button variant="primary" onClick={handleSubmit} loading={loading} disabled={loading} className="flex-1">
            {loading ? 'Running inference…' : `Run Inference (${mode === 'zip' ? 'ZIP' : files.length + ' files'})`}
          </Button>
          <Button variant="secondary" onClick={() => setFiles([])} disabled={loading}>
            Clear
          </Button>
        </div>
      )}
    </div>
  );
}
