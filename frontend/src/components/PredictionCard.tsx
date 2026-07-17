/**
 * PredictionCard — displays a single PredictionResult with class badge,
 * confidence bar, top-K list, timing, and optional Grad-CAM path.
 */

import type { PredictionResult } from '@/types';

const CLASS_COLORS: Record<string, { bg: string; text: string; bar: string; border: string }> = {
  glioma:      { bg: 'bg-red-50',    text: 'text-red-700',    bar: 'bg-red-500',    border: 'border-red-200' },
  meningioma:  { bg: 'bg-amber-50',  text: 'text-amber-700',  bar: 'bg-amber-500',  border: 'border-amber-200' },
  pituitary:   { bg: 'bg-purple-50', text: 'text-purple-700', bar: 'bg-purple-500', border: 'border-purple-200' },
  notumor:     { bg: 'bg-green-50',  text: 'text-green-700',  bar: 'bg-green-500',  border: 'border-green-200' },
};

const defaultColors = { bg: 'bg-pipeline-50', text: 'text-pipeline-700', bar: 'bg-blue-500', border: 'border-pipeline-200' };

interface Props {
  result: PredictionResult;
  showTopK?: boolean;
  showTiming?: boolean;
  showGradcam?: boolean;
  compact?: boolean;
}

export default function PredictionCard({
  result,
  showTopK = true,
  showTiming = true,
  showGradcam = true,
  compact = false,
}: Props) {
  const cls = result.predicted_class;
  const colors = CLASS_COLORS[cls] ?? defaultColors;
  const pct = (result.confidence * 100).toFixed(1);
  const isTumor = cls !== 'notumor';

  return (
    <div className={`card ${colors.bg} ${colors.border} space-y-4`} data-testid="prediction-card">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-1">
            Prediction
          </p>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${colors.bg} ${colors.text} border ${colors.border}`}>
              {isTumor ? '⚠ ' : '✓ '}
              {cls.charAt(0).toUpperCase() + cls.slice(1)}
            </span>
            {result.is_high_confidence && (
              <span className="text-xs font-medium bg-green-100 text-green-700 px-2 py-0.5 rounded-full border border-green-200">
                High confidence
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${colors.text}`}>{pct}%</p>
          <p className="text-xs text-pipeline-400 mt-0.5">confidence</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="h-2.5 w-full bg-pipeline-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${colors.bar}`}
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={result.confidence * 100}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Top-K */}
      {showTopK && result.top_k.length > 1 && !compact && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Top-{result.top_k.length} Predictions
          </p>
          <div className="space-y-1.5">
            {result.top_k.map((t) => {
              const c = CLASS_COLORS[t.class_name] ?? defaultColors;
              const p = (t.probability * 100).toFixed(1);
              return (
                <div key={t.rank} className="flex items-center gap-2">
                  <span className="text-xs font-medium text-pipeline-400 w-4">{t.rank}.</span>
                  <span className={`text-xs font-semibold w-24 ${c.text}`}>{t.class_name}</span>
                  <div className="flex-1 h-1.5 bg-pipeline-200 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.bar}`} style={{ width: `${p}%` }} />
                  </div>
                  <span className="text-xs text-pipeline-500 w-10 text-right">{p}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer meta */}
      {!compact && (
        <div className="flex flex-wrap gap-4 pt-1 text-xs text-pipeline-400 border-t border-pipeline-100">
          <span>Model: <span className="font-medium text-pipeline-600">{result.metadata.model_name}</span></span>
          {showTiming && <span>Time: <span className="font-medium text-pipeline-600">{result.timing_ms.toFixed(0)} ms</span></span>}
          {result.metadata.model_version && (
            <span>Version: <span className="font-mono text-pipeline-500">{result.metadata.model_version.slice(0, 10)}</span></span>
          )}
          {showGradcam && result.metadata.gradcam_path && (
            <span className="text-blue-600">Grad-CAM generated</span>
          )}
        </div>
      )}
    </div>
  );
}
