import { useAuthContext } from '@/context/AuthContext';
import { hasMinRole, roleAllowed, type Role } from '@/types/auth';

export function useAuth() {
  const context = useAuthContext();
  const { user, isAuthenticated } = context;

  const hasRole = (minRole: Role): boolean => {
    if (!user) return false;
    return hasMinRole(user.role, minRole);
  };

  const isRoleAllowed = (allowedRoles: Role[]): boolean => {
    if (!user) return false;
    return roleAllowed(user.role, allowedRoles);
  };

  return {
    ...context,
    hasRole,
    isRoleAllowed,
    isAdmin: user?.role === 'admin',
    isResearcher: user?.role === 'researcher',
    isOperator: user?.role === 'operator',
    isViewer: user?.role === 'viewer',
  };
}
