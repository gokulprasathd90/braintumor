import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { UserPublic, LoginRequest, ChangePasswordRequest } from '@/types/auth';
import * as authApi from '@/api/auth';

interface AuthContextType {
  user: UserPublic | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isSessionExpired: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (credentials: ChangePasswordRequest) => Promise<void>;
  refreshTokens: () => Promise<string>;
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to decode JWT exp
function getJwtExpiry(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(window.atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.exp ? payload.exp * 1000 : null; // in milliseconds
  } catch (e) {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSessionExpired, setIsSessionExpired] = useState<boolean>(false);

  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Clear all tokens and user from local state and storage
  const handleLogoutState = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('auth_user');
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const logout = useCallback(async () => {
    const rToken = localStorage.getItem('refresh_token') || refreshToken;
    try {
      if (rToken) {
        await authApi.logout(rToken);
      }
    } catch (e) {
      console.error('Logout API call failed:', e);
    } finally {
      handleLogoutState();
    }
  }, [refreshToken, handleLogoutState]);

  // Refresh token logic
  const refreshTokens = useCallback(async (): Promise<string> => {
    const storedRefreshToken = localStorage.getItem('refresh_token') || refreshToken;
    if (!storedRefreshToken) {
      handleLogoutState();
      throw new Error('No refresh token available');
    }

    try {
      const data = await authApi.refreshAccessToken(storedRefreshToken);
      const newAccessToken = data.access_token;
      
      setAccessToken(newAccessToken);
      localStorage.setItem('access_token', newAccessToken);
      
      // Reschedule auto-refresh
      scheduleAutoRefresh(newAccessToken);
      
      return newAccessToken;
    } catch (err) {
      console.error('Token refresh failed:', err);
      setIsSessionExpired(true);
      handleLogoutState();
      throw err;
    }
  }, [refreshToken, handleLogoutState]);

  // Schedule auto refresh of access token 2 minutes before expiry
  const scheduleAutoRefresh = useCallback((token: string) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    const expiryTime = getJwtExpiry(token);
    if (!expiryTime) return;

    const bufferMs = 2 * 60 * 1000; // 2 minutes
    const delay = expiryTime - Date.now() - bufferMs;

    if (delay <= 0) {
      // Access token is already close to or past expiry, refresh immediately
      refreshTokens().catch(() => {});
    } else {
      refreshTimerRef.current = setTimeout(() => {
        refreshTokens().catch(() => {});
      }, delay);
    }
  }, [refreshTokens]);

  const login = useCallback(async (credentials: LoginRequest) => {
    setIsSessionExpired(false);
    setIsLoading(true);
    try {
      const data = await authApi.login(credentials);
      setUser(data.user);
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));

      scheduleAutoRefresh(data.access_token);
    } catch (err) {
      handleLogoutState();
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleLogoutState, scheduleAutoRefresh]);

  const changePassword = useCallback(async (credentials: ChangePasswordRequest) => {
    await authApi.changePassword(credentials);
  }, []);

  const clearSessionExpired = useCallback(() => {
    setIsSessionExpired(false);
  }, []);

  // Initialize auth state from storage on mount
  useEffect(() => {
    const handleSessionExpiredEvent = () => {
      setIsSessionExpired(true);
      handleLogoutState();
    };

    window.addEventListener('auth:session_expired', handleSessionExpiredEvent);

    const initializeAuth = async () => {
      const storedAccessToken = localStorage.getItem('access_token');
      const storedRefreshToken = localStorage.getItem('refresh_token');
      const storedUser = localStorage.getItem('auth_user');

      if (storedAccessToken && storedRefreshToken && storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setAccessToken(storedAccessToken);
          setRefreshToken(storedRefreshToken);

          // Verify if access token is already expired
          const expiryTime = getJwtExpiry(storedAccessToken);
          if (expiryTime && expiryTime <= Date.now()) {
            // Attempt to refresh
            await refreshTokens();
          } else {
            // Token is still valid, schedule its refresh
            scheduleAutoRefresh(storedAccessToken);
          }
        } catch (e) {
          console.error('Error during initial auth verification:', e);
          handleLogoutState();
        }
      }
      setIsLoading(false);
    };

    initializeAuth();

    return () => {
      window.removeEventListener('auth:session_expired', handleSessionExpiredEvent);
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  const value = {
    user,
    accessToken,
    refreshToken,
    isLoading,
    isAuthenticated: !!accessToken,
    isSessionExpired,
    login,
    logout,
    changePassword,
    refreshTokens,
    clearSessionExpired,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};
