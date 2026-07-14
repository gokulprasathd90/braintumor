/**
 * src/utils/metricsExport.test.ts
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { exportMetricsJson, exportMetricsCsv, exportObjectArrayCsv } from './metricsExport';
import type { RecentPrediction } from '@/types';

// ── Helpers ────────────────────────────────────────────────────────────────

function captureDownload(): { content: string; filename: string; mimeType: string } | null {
  const calls = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls;
  if (calls.length === 0) return null;
  const blob = calls[calls.length - 1][0] as Blob;
  // We can't read blob in jsdom, but we can verify the anchor was created
  return { content: '', filename: '', mimeType: blob.type };
}

const PREDICTION: RecentPrediction = {
  image_id: 'img-001',
  model_name: 'efficientnet',
  predicted_class: 'glioma',
  confidence: 0.9218,
  timing_ms: 38.5,
  success: true,
  timestamp: '2024-07-14T12:00:00Z',
};

describe('exportMetricsJson', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('does not throw for a simple object', () => {
    expect(() => exportMetricsJson({ cpu: 42 }, 'test.json')).not.toThrow();
  });

  it('calls URL.createObjectURL with a Blob', () => {
    exportMetricsJson({ cpu: 42 }, 'metrics.json');
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
  });

  it('creates a link element and clicks it', () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    exportMetricsJson({ test: 1 }, 'out.json');
    expect(clickSpy).toHaveBeenCalledOnce();
    clickSpy.mockRestore();
  });

  it('calls URL.revokeObjectURL after download', () => {
    exportMetricsJson({ test: 1 }, 'out.json');
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });

  it('passes JSON mime type', () => {
    exportMetricsJson({ test: 1 }, 'out.json');
    const blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0][0] as Blob;
    expect(blob.type).toContain('application/json');
  });

  it('handles null / undefined values in data', () => {
    expect(() => exportMetricsJson({ a: null, b: undefined }, 'out.json')).not.toThrow();
  });
});

describe('exportMetricsCsv', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('does not throw for a valid predictions array', () => {
    expect(() => exportMetricsCsv([PREDICTION], 'predictions.csv')).not.toThrow();
  });

  it('does nothing when predictions array is empty', () => {
    exportMetricsCsv([], 'predictions.csv');
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('calls URL.createObjectURL with CSV mime type', () => {
    exportMetricsCsv([PREDICTION], 'predictions.csv');
    const blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0][0] as Blob;
    expect(blob.type).toContain('text/csv');
  });

  it('triggers a download click', () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    exportMetricsCsv([PREDICTION], 'out.csv');
    expect(clickSpy).toHaveBeenCalledOnce();
    clickSpy.mockRestore();
  });

  it('handles null confidence / predicted_class gracefully', () => {
    const pred: RecentPrediction = {
      ...PREDICTION,
      predicted_class: null,
      confidence: null,
    };
    expect(() => exportMetricsCsv([pred], 'out.csv')).not.toThrow();
  });

  it('handles multiple predictions', () => {
    const preds = Array.from({ length: 10 }, (_, i) => ({
      ...PREDICTION,
      image_id: `img-${i}`,
    }));
    expect(() => exportMetricsCsv(preds, 'bulk.csv')).not.toThrow();
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
  });
});

describe('exportObjectArrayCsv', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('exports an array of objects', () => {
    const rows = [
      { name: 'glioma', count: 67 },
      { name: 'notumor', count: 44 },
    ];
    expect(() => exportObjectArrayCsv(rows, 'dist.csv')).not.toThrow();
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
  });

  it('does nothing when array is empty', () => {
    exportObjectArrayCsv([], 'empty.csv');
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('handles values that contain commas', () => {
    const rows = [{ label: 'hello, world', value: 42 }];
    expect(() => exportObjectArrayCsv(rows, 'comma.csv')).not.toThrow();
  });

  it('handles values that contain quotes', () => {
    const rows = [{ label: 'he said "hi"', value: 1 }];
    expect(() => exportObjectArrayCsv(rows, 'quotes.csv')).not.toThrow();
  });
});
