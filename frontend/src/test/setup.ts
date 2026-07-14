/**
 * src/test/setup.ts — Vitest global test setup.
 * Imported via vite.config.ts → test.setupFiles.
 */

import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Automatically unmount React trees after every test
afterEach(() => {
  cleanup();
});

// Silence noisy console.error in tests (e.g. React act() warnings)
const originalError = console.error.bind(console);
console.error = (...args: unknown[]) => {
  const msg = String(args[0]);
  if (
    msg.includes('Warning: An update to') ||
    msg.includes('act(') ||
    msg.includes('inside a test was not wrapped in act')
  ) {
    return;
  }
  originalError(...args);
};

// Stub ResizeObserver (used by Recharts ResponsiveContainer, not in jsdom)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Stub URL.createObjectURL / revokeObjectURL (not in jsdom) without breaking URL constructor
if (typeof URL.createObjectURL === 'undefined') {
  Object.defineProperty(URL, 'createObjectURL', { value: vi.fn(() => 'blob:mock-url'), writable: true });
}
if (typeof URL.revokeObjectURL === 'undefined') {
  Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), writable: true });
}

// Stub import.meta.env values consumed by the source modules
Object.defineProperty(import.meta, 'env', {
  value: {
    VITE_API_TIMEOUT_MS: '30000',
    VITE_TRAINING_TIMEOUT_MS: '600000',
    VITE_TRAINING_POLL_INTERVAL_MS: '3000',
    VITE_AI_SERVICE_URL: 'http://localhost:8000',
  },
  writable: true,
});
