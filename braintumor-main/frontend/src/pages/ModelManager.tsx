/**
 * ModelManager — list all models, inspect cache stats, and hot-reload.
 */

import Layout from '@/components/Layout';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { ToastContainer, useToast } from '@/components/Toast';
import { useModels } from '@/hooks/useModels';

export default function ModelManager() {
  const { models, cacheStats, activeModel, reload, loading, reloading, error, refresh } = useModels();
  const { toasts, addToast, dismissToast } = useToast();

  const handleReload = async (name: string) => {
    const ok = await reload(name);
    addToast(ok ? 'success' : 'error', ok ? `Model '${name}' reloaded` : error?.detail ?? 'Reload failed');
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-pipeline-900">Model Manager</h1>
            <p className="text-pipeline-500 mt-1 text-sm">View availability, cache status, and hot-reload models.</p>
          </div>
          <Button variant="secondary" onClick={refresh} loading={loading}>Refresh</Button>
        </div>

        {/* Active model */}
        {activeModel && (
          <div className="card bg-blue-50 border-blue-200">
            <p className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-1">Active Model</p>
            <p className="text-xl font-bold text-blue-700 capitalize">{activeModel.model_name}</p>
            <p className="text-xs text-blue-500 mt-1">
              Cached: {activeModel.cached ? 'Yes' : 'No'} · Hit rate: {((activeModel.cache_stats.hit_rate ?? 0) * 100).toFixed(1)}%
            </p>
          </div>
        )}

        {/* Cache stats */}
        {cacheStats && (
          <div className="card">
            <h2 className="section-title">Cache Statistics</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              {[
                { label: 'Capacity', value: cacheStats.capacity },
                { label: 'Loaded',   value: cacheStats.size },
                { label: 'Hits',     value: cacheStats.total_hits },
                { label: 'Hit Rate', value: `${(cacheStats.hit_rate * 100).toFixed(1)}%` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-pipeline-50 rounded-xl px-3 py-3 text-center border border-pipeline-100">
                  <p className="text-xl font-bold text-pipeline-800">{value}</p>
                  <p className="text-xs text-pipeline-400 mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Model list */}
        <div className="card">
          <h2 className="section-title">All Models</h2>
          {loading && <LoadingSpinner variant="card" message="Loading models…" />}
          {!loading && (
            <div className="space-y-3">
              {models.map((m) => (
                <div key={m.name} className={`flex items-center justify-between gap-3 rounded-xl px-4 py-3 border
                  ${m.available ? 'bg-white border-pipeline-200' : 'bg-pipeline-50 border-pipeline-100'}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${m.available ? 'bg-green-500' : 'bg-pipeline-300'}`} />
                    <div className="min-w-0">
                      <p className="font-semibold text-pipeline-800 capitalize">{m.name}</p>
                      <div className="flex flex-wrap gap-2 mt-0.5">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${m.cached ? 'bg-blue-100 text-blue-700' : 'bg-pipeline-100 text-pipeline-500'}`}>
                          {m.cached ? '● cached' : '○ not cached'}
                        </span>
                        {m.total_params != null && (
                          <span className="text-xs text-pipeline-400">{(m.total_params / 1e6).toFixed(1)}M params</span>
                        )}
                        {m.model_version && (
                          <span className="text-xs font-mono text-pipeline-400">{m.model_version.slice(0, 10)}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  {m.available && (
                    <Button variant="secondary" onClick={() => handleReload(m.name)} loading={reloading}
                      className="flex-shrink-0 text-xs py-1.5 px-3">
                      Hot Reload
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <div className="card bg-red-50 border-red-200 text-sm text-red-700">{error.detail}</div>}
      </div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </Layout>
  );
}
