/**
 * DatasetSummary — compact stats card for a DatasetInfo object.
 */

import type { DatasetInfo } from '@/types';

interface Props {
  info: DatasetInfo;
}

export default function DatasetSummary({ info }: Props) {
  const splits = info.total_per_split;

  return (
    <div className="space-y-4" data-testid="dataset-summary">
      {/* Split counts */}
      <div className="grid grid-cols-3 gap-3">
        {(['train', 'val', 'test'] as const).map((split) => (
          <div key={split} className="bg-pipeline-50 rounded-xl p-4 text-center border border-pipeline-100">
            <p className="text-2xl font-bold text-blue-600">{splits[split].toLocaleString()}</p>
            <p className="text-xs text-pipeline-500 mt-1 capitalize font-medium">{split}</p>
          </div>
        ))}
      </div>

      {/* Class distribution */}
      {info.per_class_counts && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Per-Class Distribution
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs rounded-xl overflow-hidden border border-pipeline-200">
              <thead className="bg-pipeline-50">
                <tr>
                  <th className="px-3 py-2 text-left text-pipeline-500 font-semibold">Class</th>
                  <th className="px-3 py-2 text-right text-pipeline-500 font-semibold">Train</th>
                  <th className="px-3 py-2 text-right text-pipeline-500 font-semibold">Val</th>
                  <th className="px-3 py-2 text-right text-pipeline-500 font-semibold">Test</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pipeline-100 bg-white">
                {Object.entries(info.per_class_counts).map(([cls, counts]) => (
                  <tr key={cls} className="hover:bg-pipeline-50">
                    <td className="px-3 py-2 font-medium text-pipeline-700 capitalize">{cls}</td>
                    <td className="px-3 py-2 text-right text-pipeline-600">{counts.train}</td>
                    <td className="px-3 py-2 text-right text-pipeline-600">{counts.val}</td>
                    <td className="px-3 py-2 text-right text-pipeline-600">{counts.test}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex flex-wrap gap-4 text-xs text-pipeline-500 pt-1 border-t border-pipeline-100">
        <span>Total: <span className="font-semibold text-pipeline-700">{info.total_images.toLocaleString()}</span></span>
        <span>Classes: <span className="font-semibold text-pipeline-700">{info.classes.length}</span></span>
        <span>Balanced: <span className={`font-semibold ${info.is_balanced ? 'text-green-600' : 'text-amber-600'}`}>{info.is_balanced ? 'Yes' : 'No'}</span></span>
        <span>Imbalance ratio: <span className="font-semibold text-pipeline-700">{info.imbalance_ratio.toFixed(2)}</span></span>
      </div>
    </div>
  );
}
