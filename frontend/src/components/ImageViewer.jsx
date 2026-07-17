/**
 * ImageViewer
 *
 * Displays pipeline stage images returned by GET /api/results/:imageId.
 * The backend now returns URL-suffixed keys so images can be loaded directly.
 *
 * Expected `paths` shape:
 *   {
 *     raw_url:       "/uploads/<filename>",
 *     resized_url:   "/processed/resized/<filename>",
 *     enhanced_url:  "/processed/enhanced/<filename>",
 *     denoised_url:  "/processed/noise_removed/<filename>",
 *     segmented_url: "/processed/segmented/<filename>",
 *   }
 *
 * All paths are relative — the browser resolves them against the Vite dev
 * server (port 3000) which proxies /uploads, /processed, /gradcam → port 5000.
 */

const STAGES = [
  { key: 'raw_url',       label: 'Original' },
  { key: 'resized_url',   label: 'Resized (256×256)' },
  { key: 'enhanced_url',  label: 'ACEA Enhanced' },
  { key: 'denoised_url',  label: 'Median Filtered' },
  { key: 'segmented_url', label: 'FCM Segmented' },
];

export default function ImageViewer({ paths = {} }) {
  const available = STAGES.filter((s) => paths[s.key]);

  if (available.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 rounded-lg border border-dashed border-pipeline-200 text-sm text-pipeline-400">
        No pipeline images available
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {available.map(({ key, label }) => (
        <div key={key} className="flex flex-col items-center gap-1.5">
          <div className="w-full aspect-square rounded-lg overflow-hidden border border-pipeline-200 bg-black">
            <img
              src={paths[key]}
              alt={label}
              className="w-full h-full object-contain"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                const sibling = e.currentTarget.nextSibling;
                if (sibling) sibling.style.display = 'flex';
              }}
            />
            <div
              className="hidden h-full items-center justify-center text-xs text-pipeline-400 p-2 text-center"
            >
              {label}<br />not available
            </div>
          </div>
          <p className="text-xs text-pipeline-500 text-center leading-tight">{label}</p>
        </div>
      ))}
    </div>
  );
}
