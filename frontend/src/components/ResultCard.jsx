export default function ResultCard({ prediction, confidence }) {
  const isAbnormal = prediction?.toLowerCase() === 'abnormal';
  const pct = confidence != null ? (confidence * 100).toFixed(1) : null;

  const palette = isAbnormal
    ? { bg: 'bg-abnormal-50', border: 'border-abnormal-200', text: 'text-abnormal-700', bar: 'bg-abnormal-500', iconColor: 'text-abnormal-600' }
    : { bg: 'bg-normal-50',   border: 'border-normal-200',   text: 'text-normal-700',   bar: 'bg-normal-500',   iconColor: 'text-normal-600'   };

  return (
    <div className={`card ${palette.bg} ${palette.border}`}>
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={`mt-0.5 flex-shrink-0 ${palette.iconColor}`}>
          {isAbnormal ? (
            <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          ) : (
            <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>

        {/* Text */}
        <div className="flex-1">
          <p className={`text-2xl font-bold ${palette.text}`}>
            {isAbnormal ? 'Tumor Detected' : 'No Tumor Detected'}
          </p>
          <p className={`text-sm mt-1 ${palette.text} opacity-80`}>
            Classification: <span className="font-semibold capitalize">{prediction ?? '—'}</span>
          </p>

          {pct != null && (
            <div className="mt-3">
              <div className="flex justify-between text-xs font-medium mb-1">
                <span className={palette.text}>Confidence</span>
                <span className={palette.text}>{pct}%</span>
              </div>
              <div className="h-2 rounded-full bg-pipeline-200 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${palette.bar}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )}

          <p className="mt-3 text-xs text-pipeline-500">
            {isAbnormal
              ? 'Please consult a qualified medical professional for further evaluation.'
              : 'No anomalies detected. Continue regular medical check-ups.'}
          </p>
        </div>
      </div>
    </div>
  );
}
