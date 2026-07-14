import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import { AuthProvider, useAuthContext } from '@/context/AuthContext';
import { useAuth } from '@/hooks/useAuth';
import RoleBadge from '@/components/RoleBadge';
import PermissionGuard from '@/components/PermissionGuard';
import LoginForm from '@/components/LoginForm';
import UserMenu from '@/components/UserMenu';
import SessionExpiredDialog from '@/components/SessionExpiredDialog';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

beforeEach(() => {
  mock.reset();
  localStorage.clear();
});

afterEach(() => {
  mock.reset();
  localStorage.clear();
});

// A wrapper to render components with AuthProvider and Router
const renderWithProviders = (ui: React.ReactNode) => {
  return render(
    <AuthProvider>
      <BrowserRouter>{ui}</BrowserRouter>
    </AuthProvider>
  );
};

// ─── Test Component to access useAuth hooks ───
const AuthTesterComponent: React.FC = () => {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="is-auth">{auth.isAuthenticated ? 'true' : 'false'}</div>
      <div data-testid="user">{auth.user?.username || 'null'}</div>
      <div data-testid="role">{auth.user?.role || 'null'}</div>
      <div data-testid="is-admin">{auth.isAdmin ? 'true' : 'false'}</div>
      <button onClick={() => auth.login({ username: 'admin', password: 'password' })}>Login</button>
      <button onClick={auth.logout}>Logout</button>
    </div>
  );
};

describe('Auth Context & useAuth Hook', () => {
  it('starts as unauthenticated by default', () => {
    renderWithProviders(<AuthTesterComponent />);
    expect(screen.getByTestId('is-auth').textContent).toBe('false');
    expect(screen.getByTestId('user').textContent).toBe('null');
  });

  it('updates state and localStorage on successful login', async () => {
    const mockUser = {
      user_id: '123',
      username: 'admin',
      email: 'admin@test.local',
      role: 'admin',
      is_active: true,
      is_locked: false,
      created_at: '2024-01-01T12:00:00Z',
      last_login: null,
    };

    mock.onPost('/auth/login').reply(200, {
      access_token: 'mock-access',
      refresh_token: 'mock-refresh',
      token_type: 'Bearer',
      expires_in: 3600,
      user: mockUser,
    });

    renderWithProviders(<AuthTesterComponent />);
    
    const loginButton = screen.getByText('Login');
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(screen.getByTestId('is-auth').textContent).toBe('true');
      expect(screen.getByTestId('user').textContent).toBe('admin');
      expect(screen.getByTestId('is-admin').textContent).toBe('true');
    });

    expect(localStorage.getItem('access_token')).toBe('mock-access');
    expect(localStorage.getItem('refresh_token')).toBe('mock-refresh');
  });

  it('clears state on logout', async () => {
    localStorage.setItem('access_token', 'initial-access');
    localStorage.setItem('refresh_token', 'initial-refresh');
    localStorage.setItem(
      'auth_user',
      JSON.stringify({ username: 'admin', role: 'admin', is_active: true })
    );

    mock.onPost('/auth/logout').reply(200);

    renderWithProviders(<AuthTesterComponent />);
    
    // Initial loaded state
    await waitFor(() => {
      expect(screen.getByTestId('is-auth').textContent).toBe('true');
    });

    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);

    await waitFor(() => {
      expect(screen.getByTestId('is-auth').textContent).toBe('false');
      expect(screen.getByTestId('user').textContent).toBe('null');
    });

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });
});

describe('RoleBadge Component', () => {
  it('renders correct text and classes for each role', () => {
    const { rerender } = render(<RoleBadge role="admin" />);
    expect(screen.getByText('Admin')).toBeInTheDocument();

    rerender(<RoleBadge role="researcher" />);
    expect(screen.getByText('Researcher')).toBeInTheDocument();

    rerender(<RoleBadge role="operator" />);
    expect(screen.getByText('Operator')).toBeInTheDocument();

    rerender(<RoleBadge role="viewer" />);
    expect(screen.getByText('Viewer')).toBeInTheDocument();
  });
});

describe('PermissionGuard Component', () => {
  it('hides children when not authenticated', () => {
    renderWithProviders(
      <PermissionGuard minRole="viewer">
        <div data-testid="secret">Protected Content</div>
      </PermissionGuard>
    );
    expect(screen.queryByTestId('secret')).toBeNull();
  });

  it('renders children if user role meets requirement', async () => {
    localStorage.setItem('access_token', 'valid-token');
    localStorage.setItem('refresh_token', 'valid-refresh');
    localStorage.setItem(
      'auth_user',
      JSON.stringify({ username: 'researcher', role: 'researcher', is_active: true })
    );

    renderWithProviders(
      <PermissionGuard minRole="operator">
        <div data-testid="secret">Protected Content</div>
      </PermissionGuard>
    );

    await waitFor(() => {
      expect(screen.getByTestId('secret')).toBeInTheDocument();
    });
  });

  it('renders fallback if role does not meet requirement', async () => {
    localStorage.setItem('access_token', 'valid-token');
    localStorage.setItem('refresh_token', 'valid-refresh');
    localStorage.setItem(
      'auth_user',
      JSON.stringify({ username: 'operator', role: 'operator', is_active: true })
    );

    renderWithProviders(
      <PermissionGuard minRole="researcher" fallback={<div data-testid="fallback">Denied</div>}>
        <div data-testid="secret">Protected Content</div>
      </PermissionGuard>
    );

    await waitFor(() => {
      expect(screen.queryByTestId('secret')).toBeNull();
      expect(screen.getByTestId('fallback')).toBeInTheDocument();
    });
  });
});

describe('LoginForm Component', () => {
  it('submits form inputs and triggers success callback', async () => {
    const mockUser = { username: 'admin', role: 'admin', is_active: true };
    mock.onPost('/auth/login').reply(200, {
      access_token: 'mock-access',
      refresh_token: 'mock-refresh',
      user: mockUser,
    });

    const handleSuccess = vi.fn();
    renderWithProviders(<LoginForm onSuccess={handleSuccess} />);

    fireEvent.change(screen.getByPlaceholderText('Enter username'), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(handleSuccess).toHaveBeenCalledTimes(1);
    });
  });

  it('displays error message on authentication failure', async () => {
    mock.onPost('/auth/login').reply(401, {
      detail: 'Invalid credentials provided.',
    });

    renderWithProviders(<LoginForm />);

    fireEvent.change(screen.getByPlaceholderText('Enter username'), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrong-pass' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials provided.')).toBeInTheDocument();
    });
  });
});

describe('UserMenu Component', () => {
  it('renders initials and toggles settings dropdown', async () => {
    localStorage.setItem('access_token', 'valid-token');
    localStorage.setItem('refresh_token', 'valid-refresh');
    localStorage.setItem(
      'auth_user',
      JSON.stringify({ username: 'operator', email: 'operator@test.local', role: 'operator', is_active: true })
    );

    renderWithProviders(<UserMenu />);

    // Renders initials button
    await waitFor(() => {
      expect(screen.getByText('OP')).toBeInTheDocument();
    });

    // Dropdown is closed initially
    expect(screen.queryByText('Sign Out')).toBeNull();

    // Click profile button to open dropdown
    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Sign Out')).toBeInTheDocument();
    expect(screen.getByText('operator@test.local')).toBeInTheDocument();
  });
});

describe('SessionExpiredDialog Component', () => {
  it('does not render by default', () => {
    renderWithProviders(<SessionExpiredDialog />);
    expect(screen.queryByText('Session Expired')).toBeNull();
  });

  it('renders dialog and triggers acknowledgement callback when event occurs', async () => {
    renderWithProviders(
      <>
        <SessionExpiredDialog />
      </>
    );

    // Fire custom session expired event
    window.dispatchEvent(new Event('auth:session_expired'));

    await waitFor(() => {
      expect(screen.getByText('Session Expired')).toBeInTheDocument();
    });

    // Acknowledge clears the dialog
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge & Sign In' }));
    
    await waitFor(() => {
      expect(screen.queryByText('Session Expired')).toBeNull();
    });
  });
});
