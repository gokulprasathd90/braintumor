/**
 * QualityCheckPanel — renders a QualityReport with pass/fail indicators
 * for each check and a summary verdict.
 */

import type { QualityReport } from '@/types';

interface Props {
  report: QualityReport;
}

export default function QualityCheckPanel({ report }: Props) {
  return (
    <div className="space-y-4" data-testid="quality-check-panel">
      {/* Verdict */}
      <div className={`flex items-center gap-3 rounded-xl px-4 py-3 border ${report.is_valid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
        <div className={`w-3 h-3 rounded-full flex-shrink-0 ${report.is_valid ? 'bg-green-500' : 'bg-red-500'}`} />
        <div>
          <p className={`text-sm font-semibold ${report.is_valid ? 'text-green-700' : 'text-red-700'}`}>
            {report.is_valid ? 'All quality checks passed' : 'Quality check failed'}
          </p>
          <p className="text-xs text-pipeline-500 mt-0.5">
            {report.image_width} × {report.image_height} px · {(report.file_size_bytes / 1024).toFixed(1)} KB
          </p>
        </div>
      </div>

      {/* Individual checks */}
      <div className="space-y-2">
        {report.checks.map((check) => (
          <div key={check.name}
            className={`flex items-start gap-3 rounded-lg px-3 py-2.5 border text-sm ${check.passed ? 'bg-white border-pipeline-100' : 'bg-red-50 border-red-200'}`}>
            <span className={`mt-0.5 flex-shrink-0 text-lg leading-none ${check.passed ? 'text-green-500' : 'text-red-500'}`}>
              {check.passed ? '✓' : '✗'}
            </span>
            <div className="flex-1 min-w-0">
              <span className="font-medium text-pipeline-700 capitalize">{check.name.replace(/_/g, ' ')}</span>
              <span className="text-pipeline-400 ml-2 text-xs">{check.message}</span>
            </div>
            <span className="text-xs font-mono text-pipeline-500 flex-shrink-0">{check.value}</span>
          </div>
        ))}
      </div>

      {/* Warnings */}
      {report.warnings.length > 0 && (
        <div className="space-y-1.5">
          {report.warnings.map((w, i) => (
            <div key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              ⚠ {w}
            </div>
          ))}
        </div>
      )}

      {/* Errors */}
      {report.errors.length > 0 && (
        <div className="space-y-1.5">
          {report.errors.map((e, i) => (
            <div key={i} className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              ✗ {e}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
