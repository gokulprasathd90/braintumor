/**
 * PredictionTable — tabular view of BatchPredictionResult items.
 * Shows filename, status, predicted class, confidence, and timing.
 */

import { useState } from 'react';
import type { BatchPredictionResult } from '@/types';

const CLASS_BADGES: Record<string, string> = {
  glioma:     'bg-red-100 text-red-700',
  meningioma: 'bg-amber-100 text-amber-700',
  pituitary:  'bg-purple-100 text-purple-700',
  notumor:    'bg-green-100 text-green-700',
};

interface Props {
  result: BatchPredictionResult;
  onDownloadCSV?: () => void;
  onDownloadJSON?: () => void;
}

export default function PredictionTable({ result, onDownloadCSV, onDownloadJSON }: Props) {
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;
  const totalPages = Math.ceil(result.results.length / PAGE_SIZE);
  const visible = result.results.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="space-y-3" data-testid="prediction-table">
      {/* Summary bar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-4 text-sm">
          <span className="text-pipeline-500">Total: <span className="font-semibold text-pipeline-800">{result.total}</span></span>
          <span className="text-green-600">✓ {result.succeeded}</span>
          {result.failed > 0 && <span className="text-red-600">✗ {result.failed}</span>}
          <span className="text-pipeline-400">{result.timing_ms.toFixed(0)} ms</span>
        </div>
        <div className="flex gap-2">
          {onDownloadCSV && (
            <button onClick={onDownloadCSV}
              className="text-xs font-medium text-blue-600 hover:text-blue-800 border border-blue-200 rounded-lg px-3 py-1.5 hover:bg-blue-50 transition-colors">
              ↓ CSV
            </button>
          )}
          {onDownloadJSON && (
            <button onClick={onDownloadJSON}
              className="text-xs font-medium text-blue-600 hover:text-blue-800 border border-blue-200 rounded-lg px-3 py-1.5 hover:bg-blue-50 transition-colors">
              ↓ JSON
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-pipeline-200">
        <table className="min-w-full text-sm" role="table">
          <thead className="bg-pipeline-50">
            <tr>
              {['#', 'Filename', 'Status', 'Predicted Class', 'Confidence', 'Timing'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-pipeline-100 bg-white">
            {visible.map((item, i) => (
              <tr key={item.filename + i} className="hover:bg-pipeline-50 transition-colors">
                <td className="px-4 py-3 text-xs text-pipeline-400">{page * PAGE_SIZE + i + 1}</td>
                <td className="px-4 py-3">
                  <span className="text-pipeline-700 font-mono text-xs truncate max-w-[200px] block" title={item.filename}>
                    {item.filename}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {item.success
                    ? <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-200">✓ OK</span>
                    : <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200" title={item.error ?? ''}>✗ Error</span>
                  }
                </td>
                <td className="px-4 py-3">
                  {item.result
                    ? <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${CLASS_BADGES[item.result.predicted_class] ?? 'bg-pipeline-100 text-pipeline-700'}`}>
                        {item.result.predicted_class}
                      </span>
                    : <span className="text-pipeline-300">—</span>
                  }
                </td>
                <td className="px-4 py-3 text-xs text-pipeline-600">
                  {item.result ? `${(item.result.confidence * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-3 text-xs text-pipeline-400">
                  {item.result ? `${item.result.timing_ms.toFixed(0)} ms` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-pipeline-500">
          <span>Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, result.results.length)} of {result.results.length}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="px-3 py-1.5 border border-pipeline-200 rounded-lg hover:bg-pipeline-50 disabled:opacity-40">← Prev</button>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="px-3 py-1.5 border border-pipeline-200 rounded-lg hover:bg-pipeline-50 disabled:opacity-40">Next →</button>
          </div>
        </div>
      )}
    </div>
  );
}
