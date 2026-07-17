const STAGES = [
  { key: 'raw',       label: 'Original' },
  { key: 'resized',   label: 'Resized (256×256)' },
  { key: 'enhanced',  label: 'ACEA Enhanced' },
  { key: 'denoised',  label: 'Median Filtered' },
  { key: 'segmented', label: 'FCM Segmented' },
];

/**
 * ImageViewer — shows pipeline stage images.
 * @param {{ raw, resized, enhanced, denoised, segmented }} paths
 */
export default function ImageViewer({ paths = {} }) {
  const available = STAGES.filter((s) => paths[s.key]);

  if (available.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 rounded-lg border border-dashed border-pipeline-200 text-sm text-pipeline-400">
        No images available yet
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {available.map(({ key, label }) => (
        <div key={key} className="flex flex-col items-center gap-1.5">
          <div className="w-full aspect-square rounded-lg overflow-hidden border border-pipeline-200 bg-pipeline-100">
            <img
              src={paths[key]}
              alt={label}
              className="w-full h-full object-cover"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
          </div>
          <p className="text-xs text-pipeline-500 text-center leading-tight">{label}</p>
        </div>
      ))}
    </div>
  );
}
