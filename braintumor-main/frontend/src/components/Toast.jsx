import { useEffect, useState } from 'react';

/**
 * Toast — single dismissible notification.
 *
 * Props:
 *  id        {string}  — unique key
 *  type      {string}  — 'success' | 'error' | 'info' | 'warning'
 *  message   {string}  — notification text
 *  duration  {number}  — ms before auto-dismiss (default 4000, 0 = no auto-dismiss)
 *  onDismiss {fn}      — called when toast should be removed
 */
function Toast({ type = 'info', message, duration = 4000, onDismiss }) {
  const [visible, setVisible] = useState(false);

  // Fade in on mount
  useEffect(() => {
    const show = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(show);
  }, []);

  // Auto-dismiss
  useEffect(() => {
    if (!duration) return;
    const t = setTimeout(() => handleDismiss(), duration);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duration]);

  const handleDismiss = () => {
    setVisible(false);
    // Wait for fade-out transition before removing from DOM
    setTimeout(onDismiss, 200);
  };

  const styles = {
    success: { bar: 'bg-green-500',  icon: 'text-green-500',  bg: 'bg-white border-green-200' },
    error:   { bar: 'bg-red-500',    icon: 'text-red-500',    bg: 'bg-white border-red-200'   },
    warning: { bar: 'bg-amber-500',  icon: 'text-amber-500',  bg: 'bg-white border-amber-200' },
    info:    { bar: 'bg-blue-500',   icon: 'text-blue-500',   bg: 'bg-white border-blue-200'  },
  };

  const s = styles[type] ?? styles.info;

  const icons = {
    success: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
      </svg>
    ),
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`relative flex items-start gap-3 rounded-xl border shadow-lg px-4 py-3 min-w-[280px] max-w-sm
        overflow-hidden transition-all duration-200
        ${s.bg}
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
    >
      {/* Coloured left accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${s.bar}`} />

      {/* Icon */}
      <span className={`mt-0.5 flex-shrink-0 ${s.icon}`}>{icons[type]}</span>

      {/* Message */}
      <p className="flex-1 text-sm text-pipeline-800 font-medium pr-2">{message}</p>

      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="flex-shrink-0 text-pipeline-400 hover:text-pipeline-600 transition-colors"
        aria-label="Dismiss notification"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

/**
 * ToastContainer — fixed bottom-right stack of Toast notifications.
 *
 * Props:
 *  toasts    {Array<{ id, type, message, duration }>}
 *  onDismiss {fn(id)}
 */
export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null;

  return (
    <div
      aria-label="Notifications"
      className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 items-end"
    >
      {toasts.map((t) => (
        <Toast
          key={t.id}
          type={t.type}
          message={t.message}
          duration={t.duration}
          onDismiss={() => onDismiss(t.id)}
        />
      ))}
    </div>
  );
}

/**
 * useToast — hook for managing toast state.
 *
 * Returns { toasts, addToast, dismissToast }
 *
 * Usage:
 *   const { toasts, addToast, dismissToast } = useToast();
 *   addToast('success', 'Image uploaded successfully!');
 */
export function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = (type, message, duration = 4000) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message, duration }]);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return { toasts, addToast, dismissToast };
}
