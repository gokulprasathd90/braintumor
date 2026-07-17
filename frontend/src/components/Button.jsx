import LoadingSpinner from './LoadingSpinner';

/**
 * Button — primary / secondary / danger variants.
 * @param {'primary'|'secondary'|'danger'} variant
 * @param {boolean} loading — shows spinner and disables
 * @param {boolean} disabled
 * @param {string}  className — extra Tailwind classes
 */
export default function Button({
  variant = 'primary',
  loading = false,
  disabled = false,
  children,
  className = '',
  ...rest
}) {
  const base =
    'inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const styles = {
    primary:   'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 focus:ring-blue-500',
    secondary: 'bg-white text-pipeline-700 border border-pipeline-200 hover:bg-pipeline-100 active:bg-pipeline-200 focus:ring-pipeline-400',
    danger:    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus:ring-red-500',
  };

  return (
    <button
      className={`${base} ${styles[variant] ?? styles.primary} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <LoadingSpinner size="sm" message="" />}
      {children}
    </button>
  );
}
