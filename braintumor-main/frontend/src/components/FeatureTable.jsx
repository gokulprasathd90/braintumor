const FEATURE_DEFS = [
  { key: 'entropy',     label: 'Entropy',     eq: 'Eq. 8',  desc: 'Randomness of gray-level distribution' },
  { key: 'correlation', label: 'Correlation', eq: 'Eq. 9',  desc: 'Linear dependency between pixels' },
  { key: 'energy',      label: 'Energy',      eq: 'Eq. 10', desc: 'Uniformity of GLCM' },
  { key: 'contrast',    label: 'Contrast',    eq: 'Eq. 11', desc: 'Intensity contrast between neighbors' },
  { key: 'mean',        label: 'Mean',        eq: 'Eq. 12', desc: 'Average gray-level value' },
  { key: 'std_dev',     label: 'Std Dev',     eq: 'Eq. 13', desc: 'Spread of gray-level distribution' },
  { key: 'variance',    label: 'Variance',    eq: 'Eq. 14', desc: 'Squared deviation from mean' },
];

/**
 * FeatureTable — displays extracted GLCM features.
 * @param {{ entropy, correlation, energy, contrast, mean, std_dev, variance }} features
 */
export default function FeatureTable({ features }) {
  if (!features) {
    return (
      <div className="text-sm text-pipeline-400 text-center py-8">
        Features not yet extracted
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-pipeline-200">
      <table className="min-w-full divide-y divide-pipeline-100 text-sm">
        <thead className="bg-pipeline-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">Feature</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">Equation</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-pipeline-500 uppercase tracking-wide">Value</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide hidden sm:table-cell">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-pipeline-100 bg-white">
          {FEATURE_DEFS.map(({ key, label, eq, desc }) => (
            <tr key={key} className="hover:bg-pipeline-50 transition-colors">
              <td className="px-4 py-3 font-medium text-pipeline-800">{label}</td>
              <td className="px-4 py-3 text-blue-600 font-mono text-xs">{eq}</td>
              <td className="px-4 py-3 text-right font-mono text-pipeline-700">
                {features[key] != null ? Number(features[key]).toFixed(4) : '—'}
              </td>
              <td className="px-4 py-3 text-pipeline-400 text-xs hidden sm:table-cell">{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
