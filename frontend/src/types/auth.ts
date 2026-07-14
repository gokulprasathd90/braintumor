/**
 * src/types/auth.ts — TypeScript types for authentication and authorisation.
 * Mirrors app/security/roles.py and app/security/auth.py schemas.
 */

// ─── Roles ─────────────────────────────────────────────────────────────────

export type Role = 'admin' | 'researcher' | 'operator' | 'viewer';

export const ROLES: Role[] = ['admin', 'researcher', 'operator', 'viewer'];

/** Numeric rank — lower = more privilege (admin=0) */
export const ROLE_RANK: Record<Role, number> = {
  admin:      0,
  researcher: 1,
  operator:   2,
  viewer:     3,
};

// ─── User ──────────────────────────────────────────────────────────────────

export interface UserPublic {
  user_id:    string;
  username:   string;
  email:      string;
  role:       Role;
  is_active:  boolean;
  is_locked:  boolean;
  created_at: string;   // ISO-8601
  last_login: string | null;
}

// ─── Auth requests ─────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password:     string;
}

export interface CreateUserRequest {
  username: string;
  email:    string;
  password: string;
  role:     Role;
}

// ─── Auth responses ────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token:  string;
  refresh_token: string;
  token_type:    string;
  expires_in:    number;   // seconds
  user:          UserPublic;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type:   string;
  expires_in:   number;
}

// ─── Auth context state ────────────────────────────────────────────────────

export interface AuthState {
  user:          UserPublic | null;
  accessToken:   string | null;
  refreshToken:  string | null;
  isLoading:     boolean;
  isAuthenticated: boolean;
}

export type AuthAction =
  | { type: 'LOGIN_SUCCESS';  payload: { user: UserPublic; accessToken: string; refreshToken: string } }
  | { type: 'LOGOUT' }
  | { type: 'TOKEN_REFRESHED'; payload: { accessToken: string } }
  | { type: 'SET_LOADING';     payload: boolean }
  | { type: 'SET_USER';        payload: UserPublic };

// ─── Permission helpers ────────────────────────────────────────────────────

/** Returns true if the user's role is equal to or higher-privilege than minRole. */
export function hasMinRole(userRole: Role, minRole: Role): boolean {
  return ROLE_RANK[userRole] <= ROLE_RANK[minRole];
}

/** Returns true if the user's role is in the allowed set. */
export function roleAllowed(userRole: Role, allowed: Role[]): boolean {
  return allowed.includes(userRole);
}
