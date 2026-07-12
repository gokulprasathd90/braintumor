export default function ErrorMessage({ message, onRetry }) {
  if (!message) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700"
    >
      {/* Icon */}
      <svg
        className="w-5 h-5 mt-0.5 flex-shrink-0 text-red-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
        />
      </svg>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">Error</p>
        <p className="text-sm mt-0.5 text-red-600">{message}</p>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="flex-shrink-0 text-sm font-medium text-red-700 underline hover:text-red-900"
        >
          Retry
        </button>
      )}
    </div>
  );
}
