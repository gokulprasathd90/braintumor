const variants = {
  normal:   'bg-normal-100 text-normal-700 ring-normal-500/30',
  abnormal: 'bg-abnormal-100 text-abnormal-700 ring-abnormal-500/30',
  info:     'bg-blue-50 text-blue-700 ring-blue-500/30',
  warning:  'bg-amber-50 text-amber-700 ring-amber-500/30',
  default:  'bg-pipeline-100 text-pipeline-700 ring-pipeline-500/20',
};

/**
 * Badge — small status chip.
 * @param {string} variant — 'normal' | 'abnormal' | 'info' | 'warning' | 'default'
 * @param {string} label
 */
export default function Badge({ variant = 'default', label }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${variants[variant] ?? variants.default}`}
    >
      {label}
    </span>
  );
}
