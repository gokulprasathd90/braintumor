/**
 * GradCAMViewer — displays a Grad-CAM overlay image from a file path.
 * The path is served by the ai-service's static file handler.
 */

import { useState } from 'react';

interface Props {
  gradcamPath: string | null | undefined;
  originalSrc?: string;
  altText?: string;
}

export default function GradCAMViewer({ gradcamPath, originalSrc, altText = 'Grad-CAM heatmap overlay' }: Props) {
  const [imgError, setImgError] = useState(false);

  if (!gradcamPath) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-pipeline-200 bg-pipeline-50 p-8 text-center">
        <svg className="w-10 h-10 text-pipeline-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5M4.5 3h15A1.5 1.5 0 0121 4.5v15a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 19.5v-15A1.5 1.5 0 014.5 3z" />
        </svg>
        <p className="text-sm text-pipeline-400">Grad-CAM not generated</p>
        <p className="text-xs text-pipeline-300 mt-1">Enable &ldquo;Generate Grad-CAM&rdquo; to visualise attention</p>
      </div>
    );
  }

  // Build the URL — gradcam_path is an absolute server path; proxy via /api serving
  const imgSrc = `/api/v1/gradcam/${encodeURIComponent(gradcamPath.split('/').pop() ?? '')}`;

  return (
    <div className="space-y-3" data-testid="gradcam-viewer">
      <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
        Grad-CAM Heatmap
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Original (if supplied) */}
        {originalSrc && (
          <div className="space-y-1.5">
            <p className="text-xs text-pipeline-400 font-medium text-center">Original</p>
            <div className="rounded-xl overflow-hidden border border-pipeline-200 bg-black flex items-center justify-center h-52">
              <img src={originalSrc} alt="Original MRI scan" className="max-h-full object-contain" />
            </div>
          </div>
        )}

        {/* Grad-CAM overlay */}
        <div className="space-y-1.5">
          <p className="text-xs text-blue-600 font-medium text-center">Attention Heatmap</p>
          <div className="rounded-xl overflow-hidden border border-blue-200 bg-black flex items-center justify-center h-52">
            {!imgError ? (
              <img
                src={imgSrc}
                alt={altText}
                className="max-h-full object-contain"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="text-xs text-pipeline-400 p-4 text-center">
                <p>Heatmap image not available</p>
                <p className="font-mono text-pipeline-300 mt-1 break-all text-[10px]">{gradcamPath}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-pipeline-400 bg-pipeline-50 rounded-lg px-3 py-2 border border-pipeline-100">
        Grad-CAM highlights the regions most influential to the model&apos;s prediction.
        Red/warm areas indicate high attention; blue/cool areas indicate low attention.
      </p>
    </div>
  );
}
