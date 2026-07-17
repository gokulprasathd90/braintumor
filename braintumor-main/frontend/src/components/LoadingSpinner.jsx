const sizeMap = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-2',
  lg: 'w-12 h-12 border-4',
};

export default function LoadingSpinner({
  variant = 'inline',
  message = 'Loading...',
  size = 'md',
}) {
  const spinner = (
    <div
      className={`${sizeMap[size] ?? sizeMap.md} rounded-full border-pipeline-200 border-t-blue-600 animate-spin`}
      role="status"
      aria-label="Loading"
    />
  );

  if (variant === 'overlay') {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/70 backdrop-blur-sm">
        {spinner}
        {message && <p className="mt-3 text-sm text-pipeline-600 font-medium">{message}</p>}
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        {spinner}
        {message && <p className="text-sm text-pipeline-500 font-medium">{message}</p>}
      </div>
    );
  }

  // inline (default)
  return (
    <span className="inline-flex items-center gap-2">
      {spinner}
      {message && <span className="text-sm text-pipeline-600">{message}</span>}
    </span>
  );
}
