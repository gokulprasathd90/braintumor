/**
 * src/utils/metricsExport.ts — Client-side export helpers.
 *
 * Provides utilities to download metrics data as JSON or CSV files
 * directly from the browser without a separate server round-trip.
 */

import type { RecentPrediction } from '@/types';

// ── JSON export ────────────────────────────────────────────────────────────

/**
 * Serialise `data` to a formatted JSON file and trigger a browser download.
 *
 * @param data     Any JSON-serialisable object.
 * @param filename Suggested download filename, e.g. "metrics_2024-07-14.json".
 */
export function exportMetricsJson(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2);
  triggerDownload(json, filename, 'application/json');
}

// ── CSV export ─────────────────────────────────────────────────────────────

/** Column definitions for the predictions CSV. */
const PREDICTION_COLUMNS: Array<{
  header: string;
  accessor: (p: RecentPrediction) => string;
}> = [
  { header: 'image_id',      accessor: (p) => p.image_id ?? '' },
  { header: 'model_name',    accessor: (p) => p.model_name },
  { header: 'predicted_class', accessor: (p) => p.predicted_class ?? '' },
  { header: 'confidence',    accessor: (p) => p.confidence !== null ? p.confidence.toFixed(4) : '' },
  { header: 'timing_ms',     accessor: (p) => p.timing_ms.toFixed(2) },
  { header: 'success',       accessor: (p) => String(p.success) },
  { header: 'timestamp',     accessor: (p) => p.timestamp },
];

/**
 * Export a list of recent predictions to a CSV file and trigger download.
 */
export function exportMetricsCsv(
  predictions: RecentPrediction[],
  filename: string,
): void {
  if (predictions.length === 0) return;

  const header = PREDICTION_COLUMNS.map((c) => c.header).join(',');
  const rows = predictions.map((p) =>
    PREDICTION_COLUMNS.map((c) => csvEscape(c.accessor(p))).join(','),
  );

  const csv = [header, ...rows].join('\n');
  triggerDownload(csv, filename, 'text/csv');
}

/**
 * Export any array of objects to CSV (generic).
 * All keys of the first object are used as column headers.
 */
export function exportObjectArrayCsv(
  rows: Record<string, unknown>[],
  filename: string,
): void {
  if (rows.length === 0) return;

  const headers = Object.keys(rows[0]);
  const header = headers.join(',');
  const csvRows = rows.map((row) =>
    headers.map((h) => csvEscape(String(row[h] ?? ''))).join(','),
  );

  const csv = [header, ...csvRows].join('\n');
  triggerDownload(csv, filename, 'text/csv');
}

// ── Helpers ────────────────────────────────────────────────────────────────

function csvEscape(value: string): string {
  // Wrap in quotes if value contains comma, newline, or double-quote
  if (value.includes(',') || value.includes('\n') || value.includes('"')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function triggerDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
