import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const NAV_LINKS = [
  { to: '/',        label: 'Home' },
  { to: '/detect',  label: 'Detect' },
  { to: '/results', label: 'Results' },
];

export default function Navbar() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="bg-white border-b border-pipeline-200 shadow-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Brand */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            {/* Brain icon */}
            <svg className="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.75 3A6.75 6.75 0 003 9.75c0 2.108.967 3.99 2.48 5.22A3.75 3.75 0 009 18.75h6a3.75 3.75 0 003.52-3.78A6.75 6.75 0 0021 9.75 6.75 6.75 0 0014.25 3" />
            </svg>
            <span className="font-bold text-pipeline-800 text-base leading-tight hidden sm:block">
              MRI Brain Tumor Detection
            </span>
            <span className="font-bold text-pipeline-800 text-base leading-tight sm:hidden">
              BTD
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ to, label }) => {
              const active = pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 ${
                    active
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-pipeline-600 hover:bg-pipeline-100 hover:text-pipeline-900'
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 rounded-lg text-pipeline-500 hover:bg-pipeline-100 focus:outline-none"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-pipeline-100 bg-white px-4 pb-4 pt-2 space-y-1">
          {NAV_LINKS.map(({ to, label }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={`block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-pipeline-600 hover:bg-pipeline-100 hover:text-pipeline-900'
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
