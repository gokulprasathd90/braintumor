/**
 * src/api/auth.ts — Auth API calls against /api/v1/auth/*
 *
 * All functions throw ApiError on failure (same contract as other API modules).
 */

import { apiClient } from './client';
import type {
  LoginRequest,
  TokenResponse,
  AccessTokenResponse,
  UserPublic,
  CreateUserRequest,
  ChangePasswordRequest,
} from '@/types/auth';

// ── Login ──────────────────────────────────────────────────────────────────

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>('/auth/login', credentials);
  return res.data;
}

// ── Logout ─────────────────────────────────────────────────────────────────

export async function logout(refreshToken?: string): Promise<void> {
  await apiClient.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
}

// ── Refresh access token ───────────────────────────────────────────────────

export async function refreshAccessToken(refreshToken: string): Promise<AccessTokenResponse> {
  const res = await apiClient.post<AccessTokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return res.data;
}

// ── Get current user ───────────────────────────────────────────────────────

export async function getMe(): Promise<UserPublic> {
  const res = await apiClient.get<{ success: boolean; data: UserPublic }>('/auth/me');
  return res.data.data;
}

// ── Change password ────────────────────────────────────────────────────────

export async function changePassword(body: ChangePasswordRequest): Promise<void> {
  await apiClient.post('/auth/change-password', body);
}

// ── Admin: list users ─────────────────────────────────────────────────────

export async function listUsers(): Promise<{ users: UserPublic[]; total: number }> {
  const res = await apiClient.get<{ users: UserPublic[]; total: number }>('/auth/users');
  return res.data;
}

// ── Admin: create user ────────────────────────────────────────────────────

export async function createUser(body: CreateUserRequest): Promise<UserPublic> {
  const res = await apiClient.post<{ success: boolean; data: UserPublic }>('/auth/users', body);
  return res.data.data;
}

// ── Admin: unlock user ────────────────────────────────────────────────────

export async function unlockUser(userId: string): Promise<void> {
  await apiClient.post(`/auth/users/${userId}/unlock`);
}
