/**
 * SystemHealthPanel — CPU, RAM, disk, GPU gauges + process info row.
 */

import MetricGauge from '@/components/MetricGauge';
import type { SystemMetrics } from '@/types';

interface Props {
  data: SystemMetrics;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 py-1 border-b border-pipeline-50 last:border-0">
      <span className="text-xs text-pipeline-400">{label}</span>
      <span className="text-xs font-semibold text-pipeline-700 text-right">{value}</span>
    </div>
  );
}

export default function SystemHealthPanel({ data }: Props) {
  const gpuLabel = data.gpu_available && data.gpus.length > 0
    ? `${data.gpus[0].utilization_percent ?? 0}%`
    : null;

  return (
    <div className="space-y-4" data-testid="system-health-panel">
      {/* Gauges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 justify-items-center">
        <MetricGauge label="CPU" value={data.cpu_percent} />
        <MetricGauge label="RAM" value={data.ram_percent} />
        <MetricGauge label="Disk" value={data.disk_percent} />
        {data.gpu_available ? (
          <MetricGauge
            label="GPU"
            value={data.gpus[0]?.utilization_percent ?? null}
          />
        ) : (
          <div className="flex flex-col items-center gap-1">
            <div
              className="w-[100px] h-[100px] flex items-center justify-center rounded-full border-4 border-pipeline-100 bg-pipeline-50"
              aria-label="GPU: not available"
            >
              <span className="text-xs text-pipeline-400 text-center font-medium">No GPU</span>
            </div>
            <p className="text-xs font-medium text-pipeline-500">GPU</p>
          </div>
        )}
      </div>

      {/* Info rows */}
      <div className="bg-pipeline-50 rounded-xl p-4 space-y-0.5">
        <InfoRow label="Platform" value={data.platform} />
        <InfoRow label="Python" value={data.python_version} />
        <InfoRow label="Uptime" value={formatUptime(data.uptime_seconds)} />
        <InfoRow label="Process PID" value={String(data.process_pid ?? '—')} />
        <InfoRow
          label="Process RAM"
          value={data.process_ram_mb !== null ? `${data.process_ram_mb.toFixed(0)} MB` : '—'}
        />
        <InfoRow
          label="Process Threads"
          value={String(data.process_threads ?? '—')}
        />
        {data.gpu_available && data.gpus.length > 0 && (
          <>
            <InfoRow label="GPU Name" value={data.gpus[0].name} />
            <InfoRow
              label="GPU Memory"
              value={
                data.gpus[0].memory_used_mb !== null && data.gpus[0].memory_total_mb !== null
                  ? `${data.gpus[0].memory_used_mb.toFixed(0)} / ${data.gpus[0].memory_total_mb.toFixed(0)} MB`
                  : '—'
              }
            />
          </>
        )}
        <InfoRow
          label="RAM"
          value={
            data.ram_used_mb !== null && data.ram_total_mb !== null
              ? `${(data.ram_used_mb / 1024).toFixed(1)} / ${(data.ram_total_mb / 1024).toFixed(1)} GB`
              : '—'
          }
        />
        <InfoRow
          label="Disk"
          value={
            data.disk_used_gb !== null && data.disk_total_gb !== null
              ? `${data.disk_used_gb.toFixed(1)} / ${data.disk_total_gb.toFixed(1)} GB`
              : '—'
          }
        />
      </div>

      {/* Per-core CPU bars */}
      {data.cpu_per_core.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide mb-2">
            Per-Core CPU Usage
          </p>
          <div className="flex gap-1 items-end h-12">
            {data.cpu_per_core.map((pct, i) => {
              const colour =
                pct >= 90 ? 'bg-red-400' : pct >= 70 ? 'bg-amber-400' : 'bg-green-400';
              return (
                <div
                  key={i}
                  className="flex-1 rounded-sm transition-all duration-300"
                  style={{ height: `${Math.max(4, pct)}%` }}
                  title={`Core ${i}: ${pct}%`}
                  aria-label={`Core ${i}: ${pct}%`}
                >
                  <div className={`w-full h-full rounded-sm ${colour}`} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
