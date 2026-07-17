import React from 'react';
import { useAuth } from '@/hooks/useAuth';

export const SessionExpiredDialog: React.FC = () => {
  const { isSessionExpired, clearSessionExpired } = useAuth();

  if (!isSessionExpired) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-md p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-xl animate-scale-in text-slate-100">
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-6 h-6 animate-pulse"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
            />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-center text-slate-100 tracking-tight">Session Expired</h3>
        <p className="mt-2 text-sm text-center text-slate-400">
          Your security session has ended. To protect your data, you must log in again to continue accessing the AI dashboard.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <button
            onClick={clearSessionExpired}
            className="w-full px-4 py-2.5 text-sm font-semibold rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 transition-all duration-300 shadow-lg shadow-amber-500/10 hover:shadow-amber-500/25 active:scale-[0.98] focus:outline-none"
          >
            Acknowledge & Sign In
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionExpiredDialog;
