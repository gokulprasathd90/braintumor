import React from 'react';
import type { Role } from '@/types/auth';

interface RoleBadgeProps {
  role: Role;
  className?: string;
}

export const RoleBadge: React.FC<RoleBadgeProps> = ({ role, className = '' }) => {
  const styles: Record<Role, string> = {
    admin: 'bg-red-500/10 text-red-500 border-red-500/20',
    researcher: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    operator: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    viewer: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  };

  const label: Record<Role, string> = {
    admin: 'Admin',
    researcher: 'Researcher',
    operator: 'Operator',
    viewer: 'Viewer',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${styles[role]} capitalize tracking-wide transition-all duration-300 hover:scale-[1.03] ${className}`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-80" />
      {label[role]}
    </span>
  );
};

export default RoleBadge;
