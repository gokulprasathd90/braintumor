import React from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { Role } from '@/types/auth';

interface PermissionGuardProps {
  allowedRoles?: Role[];
  minRole?: Role;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  allowedRoles,
  minRole,
  fallback = null,
  children,
}) => {
  const { user, isAuthenticated, hasRole, isRoleAllowed } = useAuth();

  if (!isAuthenticated || !user) {
    return <>{fallback}</>;
  }

  // Check roles
  let isAuthorized = true;

  if (minRole) {
    isAuthorized = hasRole(minRole);
  }

  if (allowedRoles) {
    isAuthorized = isAuthorized && isRoleAllowed(allowedRoles);
  }

  if (!isAuthorized) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export default PermissionGuard;
