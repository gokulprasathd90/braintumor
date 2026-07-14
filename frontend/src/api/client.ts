/**
 * src/api/client.ts — Axios instance for the Brain Tumour AI service.
 *
 * Features:
 *  - Base URL from VITE_AI_SERVICE_URL (proxied as /api in dev)
 *  - Configurable timeout
 *  - Request interceptor: adds Accept and Authorization headers
 *  - Response interceptor: handles 401 token refresh, unwraps envelope, or throws ApiError
 *  - Automatic retry (up to 2 times) on 5xx / network errors
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import type { ApiError } from '@/types';

// ── Constants ──────────────────────────────────────────────────────────────

const BASE_URL = '/api/v1';
const TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 30_000);
const MAX_RETRIES = 2;

// ── Create instance ────────────────────────────────────────────────────────

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT_MS,
  headers: {
    Accept: 'application/json',
  },
});

// ── Retry state stored on config ───────────────────────────────────────────

interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
  _retry?: boolean;
}

// ── Request interceptor ────────────────────────────────────────────────────

apiClient.interceptors.request.use((config: RetryConfig) => {
  config._retryCount ??= 0;
  
  // Attach JWT access token if present in localStorage
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ── Response interceptor ──────────────────────────────────────────────────

// Shared promise to prevent concurrent duplicate refresh requests
let refreshTokenPromise: Promise<string> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as (RetryConfig) | undefined;

    // ── Handle 401 Unauthorized (Token Expiry) ─────────────────────────
    if (error.response?.status === 401 && config && !config._retry) {
      config._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          if (!refreshTokenPromise) {
            // Trigger refresh call using native axios to bypass the interceptors
            refreshTokenPromise = axios
              .post<{ access_token: string }>(`${BASE_URL}/auth/refresh`, {
                refresh_token: refreshToken,
              })
              .then((res) => {
                const newToken = res.data.access_token;
                localStorage.setItem('access_token', newToken);
                return newToken;
              })
              .finally(() => {
                refreshTokenPromise = null;
              });
          }

          const newToken = await refreshTokenPromise;
          config.headers.Authorization = `Bearer ${newToken}`;
          
          // Retry original request with the new token
          return apiClient(config);
        } catch (refreshError) {
          // Token refresh failed or refresh token is expired
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('auth_user');
          
          // Notify App context that session has expired
          window.dispatchEvent(new Event('auth:session_expired'));
          
          return Promise.reject(error);
        }
      }
    }

    // ── Retry on 5xx or network error ──────────────────────────────────
    const shouldRetry =
      config &&
      (config._retryCount ?? 0) < MAX_RETRIES &&
      (!error.response || error.response.status >= 500);

    if (shouldRetry && config) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      const delay = 300 * config._retryCount;
      await new Promise((r) => setTimeout(r, delay));
      return apiClient(config);
    }

    // ── Parse error into ApiError ──────────────────────────────────────
    const status = error.response?.status ?? 0;
    const responseData = error.response?.data as Record<string, unknown> | undefined;

    const detail: string =
      (responseData?.detail as string) ||
      (responseData?.message as string) ||
      error.message ||
      'An unexpected error occurred';

    const apiError: ApiError = { detail, status };
    return Promise.reject(apiError);
  },
);

// ── Convenience helpers ────────────────────────────────────────────────────

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await apiClient.get<T>(url, config);
  return res.data;
}

export async function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.post<T>(url, data, config);
  return res.data;
}

export async function postForm<T>(url: string, formData: FormData): Promise<T> {
  const res = await apiClient.post<T>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: Number(import.meta.env.VITE_TRAINING_TIMEOUT_MS ?? 600_000),
  });
  return res.data;
}
