import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import RoleBadge from './RoleBadge';

export const UserMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  const initials = user.username.slice(0, 2).toUpperCase();

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 p-1.5 pr-3 bg-slate-900/60 border border-slate-800 rounded-xl hover:border-slate-700/60 active:scale-[0.98] transition-all duration-300 focus:outline-none"
      >
        <div className="flex items-center justify-center w-8 h-8 font-bold text-xs rounded-lg bg-gradient-to-tr from-amber-500 to-yellow-400 text-slate-950 shadow-md">
          {initials}
        </div>
        <div className="hidden md:flex flex-col items-start text-left">
          <span className="text-sm font-semibold text-slate-200 leading-tight">{user.username}</span>
          <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">{user.role}</span>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`w-4 h-4 text-slate-500 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 p-2 bg-slate-900/95 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-xl animate-scale-in origin-top-right text-slate-200 z-50">
          <div className="px-3 py-2 border-b border-slate-800/80 mb-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Signed In As</p>
            <p className="text-sm font-bold text-slate-200 truncate mt-0.5">{user.username}</p>
            <p className="text-[11px] text-slate-400 truncate mb-1.5">{user.email}</p>
            <RoleBadge role={user.role} />
          </div>

          <button
            onClick={() => {
              setIsOpen(false);
              // Profile action if any
            }}
            className="flex items-center gap-2.5 w-full px-3 py-2 text-xs font-medium rounded-xl hover:bg-slate-800/60 text-slate-300 hover:text-slate-100 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4 text-slate-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
              />
            </svg>
            My Profile
          </button>

          <button
            onClick={async () => {
              setIsOpen(false);
              await logout();
            }}
            className="flex items-center gap-2.5 w-full px-3 py-2 mt-1 text-xs font-medium rounded-xl hover:bg-red-500/10 text-red-400 hover:text-red-300 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15"
              />
            </svg>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
};

export default UserMenu;
