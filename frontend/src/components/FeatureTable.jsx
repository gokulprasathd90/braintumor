/**
 * FeatureTable
 *
 * Displays the 7 real GLCM texture features computed by scikit-image
 * from the MRI image. Each value comes from the backend API — no placeholders.
 *
 * Props:
 *   features — object from resultData.features:
 *     { entropy, correlation, energy, contrast, mean, std_dev, variance }
 */

const FEATURE_DEFS = [
  {
    key:   'entropy',
    label: 'Entropy',
    eq:    'Eq. 8',
    desc:  'Randomness of gray-level distribution — higher = more complex texture',
    range: [0, 6],
  },
  {
    key:   'correlation',
    label: 'Correlation',
    eq:    'Eq. 9',
    desc:  'Linear dependency between pixel pairs — closer to ±1 = stronger correlation',
    range: [-1, 1],
  },
  {
    key:   'energy',
    label: 'Energy',
    eq:    'Eq. 10',
    desc:  'Uniformity (sum of squared GLCM elements) — higher = more uniform texture',
    range: [0, 1],
  },
  {
    key:   'contrast',
    label: 'Contrast',
    eq:    'Eq. 11',
    desc:  'Intensity contrast between neighbouring pixels — higher = more local variation',
    range: [0, null],
  },
  {
    key:   'mean',
    label: 'Mean',
    eq:    'Eq. 12',
    desc:  'Average gray level of the texture distribution',
    range: [0, 7],
  },
  {
    key:   'std_dev',
    label: 'Std Dev',
    eq:    'Eq. 13',
    desc:  'Spread of gray-level distribution around the mean',
    range: [0, null],
  },
  {
    key:   'variance',
    label: 'Variance',
    eq:    'Eq. 14',
    desc:  'Squared deviation from mean — reflects intensity heterogeneity',
    range: [0, null],
  },
];

function MiniBar({ value, range }) {
  if (range[1] == null) return null;
  const pct = Math.min(100, Math.max(0, ((value - range[0]) / (range[1] - range[0])) * 100));
  return (
    <div className="w-16 h-1.5 rounded-full bg-pipeline-200 overflow-hidden inline-block ml-2 align-middle">
      <div className="h-full rounded-full bg-blue-400" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function FeatureTable({ features }) {
  if (!features) {
    return (
      <div className="flex flex-col items-center justify-center py-10 space-y-2 text-pipeline-400">
        <svg className="w-10 h-10 opacity-40" fill="none" viewBox="0 0 24 24"
             stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
        </svg>
        <p className="text-sm font-medium">GLCM features not available</p>
        <p className="text-xs text-center max-w-xs">
          Features are extracted automatically when the pipeline runs.
          Try uploading and running detection again.
        </p>
      </div>
    );
  }

  // Check if all values are present and non-null
  const allPresent = FEATURE_DEFS.every(({ key }) => features[key] != null);

  return (
    <div className="space-y-3">
      {!allPresent && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Some features are missing — the pipeline may not have run completely.
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border border-pipeline-200">
        <table className="min-w-full divide-y divide-pipeline-100 text-sm">
          <thead className="bg-pipeline-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                Feature
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                Eq.
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                Value
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-pipeline-500 uppercase tracking-wide hidden sm:table-cell">
                Description
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-pipeline-100 bg-white">
            {FEATURE_DEFS.map(({ key, label, eq, desc, range }) => {
              const val = features[key];
              return (
                <tr key={key} className="hover:bg-pipeline-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-pipeline-800 whitespace-nowrap">
                    {label}
                  </td>
                  <td className="px-4 py-3 text-blue-600 font-mono text-xs whitespace-nowrap">
                    {eq}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-pipeline-700 whitespace-nowrap">
                    {val != null ? (
                      <>
                        {Number(val).toFixed(4)}
                        <MiniBar value={Number(val)} range={range} />
                      </>
                    ) : (
                      <span className="text-pipeline-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-pipeline-400 text-xs hidden sm:table-cell">
                    {desc}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-pipeline-400">
        Computed using GLCM (Gray-Level Co-occurrence Matrix) at 4 directions
        (0°, 45°, 90°, 135°) with distance=1 and 8 quantization levels.
      </p>
    </div>
  );
}
