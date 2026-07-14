import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import UserMenu from './UserMenu';

const PRIMARY_LINKS = [
  { to: '/',              label: 'Dashboard' },
  { to: '/predict',       label: 'Predict' },
  { to: '/batch',         label: 'Batch' },
  { to: '/training',      label: 'Training' },
];

const MORE_LINKS = [
  { to: '/experiments',   label: 'Experiments' },
  { to: '/models',        label: 'Models' },
  { to: '/dataset',       label: 'Dataset' },
  { to: '/preprocessing', label: 'Preprocessing' },
  { to: '/monitoring',    label: 'Monitoring' },
];

const ALL_LINKS = [...PRIMARY_LINKS, ...MORE_LINKS];

export default function Navbar() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const isActive = (to: string) => pathname === to;

  return (
    <nav className="bg-slate-900 border-b border-slate-800 shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Brand */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <svg className="w-7 h-7 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.75 3A6.75 6.75 0 003 9.75c0 2.108.967 3.99 2.48 5.22A3.75 3.75 0 009 18.75h6a3.75 3.75 0 003.52-3.78A6.75 6.75 0 0021 9.75 6.75 6.75 0 0014.25 3" />
            </svg>
            <span className="font-bold text-slate-100 text-base leading-tight hidden sm:block">
              Brain Tumour Detection
            </span>
            <span className="font-bold text-slate-100 text-base sm:hidden">BTD</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-1">
              {PRIMARY_LINKS.map(({ to, label }) => (
                <Link key={to} to={to}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150
                    ${isActive(to) ? 'bg-slate-800 text-amber-500' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}>
                  {label}
                </Link>
              ))}

              {/* More dropdown */}
              <div className="relative">
                <button onClick={() => setMoreOpen((o) => !o)} onBlur={() => setTimeout(() => setMoreOpen(false), 150)}
                  className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150
                    ${MORE_LINKS.some((l) => isActive(l.to)) ? 'bg-slate-800 text-amber-500' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}>
                  More
                  <svg className={`w-3.5 h-3.5 transition-transform ${moreOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>
                {moreOpen && (
                  <div className="absolute right-0 mt-1 w-48 bg-slate-900 border border-slate-800 rounded-xl shadow-lg py-1 z-50">
                    {MORE_LINKS.map(({ to, label }) => (
                      <Link key={to} to={to} onClick={() => setMoreOpen(false)}
                        className={`block px-4 py-2.5 text-sm font-medium transition-colors
                          ${isActive(to) ? 'bg-slate-800/80 text-amber-500' : 'text-slate-400 hover:bg-slate-800/30 hover:text-slate-200'}`}>
                        {label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="border-l border-slate-800 pl-4 py-1">
              <UserMenu />
            </div>
          </div>

          {/* Mobile hamburger & UserMenu */}
          <div className="flex items-center gap-3 md:hidden">
            <UserMenu />
            <button className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 focus:outline-none"
              onClick={() => setMenuOpen((o) => !o)} aria-label="Toggle menu" aria-expanded={menuOpen}>
              {menuOpen
                ? <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                : <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" /></svg>
              }
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-900 px-4 pb-4 pt-2 space-y-1">
          {ALL_LINKS.map(({ to, label }) => (
            <Link key={to} to={to} onClick={() => setMenuOpen(false)}
              className={`block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${isActive(to) ? 'bg-slate-800 text-amber-500' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}>
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
