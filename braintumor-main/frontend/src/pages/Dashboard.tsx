/**
 * Dashboard — landing page with live health, model status, and quick-action cards.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { apiClient } from '@/api/client';
import type { HealthResponse } from '@/types';

const QUICK_ACTIONS = [
  { label: 'Single Prediction', desc: 'Classify one MRI scan instantly', to: '/predict', icon: '🧠' },
  { label: 'Batch Prediction',  desc: 'Upload multiple scans or a ZIP archive', to: '/batch', icon: '📦' },
  { label: 'Train a Model',     desc: 'Launch a training job with custom config', to: '/training', icon: '🏋️' },
  { label: 'Experiments',       desc: 'Browse past training runs', to: '/experiments', icon: '📊' },
  { label: 'Dataset Manager',   desc: 'Validate and prepare the dataset', to: '/dataset', icon: '🗂️' },
  { label: 'Model Manager',     desc: 'View, cache, and hot-reload models', to: '/models', icon: '⚙️' },
  { label: 'Monitoring',        desc: 'Live system health and analytics dashboard', to: '/monitoring', icon: '📈' },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    apiClient.get<HealthResponse>('/health')
      .then((r) => setHealth(r.data))
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false));
  }, []);

  const serviceOk = health?.status === 'ok';

  return (
    <Layout>
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Hero */}
        <section className="card text-center py-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-pipeline-900 leading-tight">
            Brain Tumour Detection
          </h1>
          <p className="mt-3 text-pipeline-500 max-w-2xl mx-auto">
            Production-grade MRI classification using CNN, VGG-16, ResNet-50, and EfficientNetB3.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
            <Button variant="primary" onClick={() => navigate('/predict')}>
              Start Prediction →
            </Button>
            <Button variant="secondary" onClick={() => navigate('/training')}>
              Train a Model
            </Button>
          </div>
        </section>

        {/* AI service status */}
        <section className="card">
          <h2 className="section-title">AI Service Status</h2>
          {healthLoading ? (
            <LoadingSpinner variant="inline" message="Checking service…" />
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${serviceOk ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className={`text-sm font-semibold ${serviceOk ? 'text-green-700' : 'text-red-700'}`}>
                  {serviceOk ? 'Online' : 'Degraded'} — {health.service}
                </span>
                <span className="text-xs text-pipeline-400 ml-auto">{health.timestamp.slice(0, 19).replace('T', ' ')} UTC</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <Stat label="Active Model" value={health.active_model} />
                <Stat label="Image Size" value={`${health.image_size} × ${health.image_size}`} />
                <Stat label="Classes" value={String(health.class_names.length)} />
                <Stat label="Environment" value={health.environment} />
              </div>
              <div>
                <p className="text-xs text-pipeline-500 mb-2">Models Available</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(health.models_available).map(([name, avail]) => (
                    <span key={name} className={`text-xs font-medium px-2.5 py-1 rounded-full border
                      ${avail ? 'bg-green-50 text-green-700 border-green-200' : 'bg-pipeline-100 text-pipeline-400 border-pipeline-200'}`}>
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-red-600">Could not reach the AI service. Make sure it is running on port 8000.</p>
          )}
        </section>

        {/* Quick actions */}
        <section>
          <h2 className="section-title">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {QUICK_ACTIONS.map(({ label, desc, to, icon }) => (
              <button key={to} onClick={() => navigate(to)}
                className="card text-left hover:border-blue-300 hover:shadow-md transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 group">
                <div className="text-2xl mb-2">{icon}</div>
                <p className="font-semibold text-pipeline-800 group-hover:text-blue-700 transition-colors">{label}</p>
                <p className="text-sm text-pipeline-500 mt-1">{desc}</p>
              </button>
            ))}
          </div>
        </section>
      </div>
    </Layout>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-pipeline-50 rounded-lg px-3 py-2 border border-pipeline-100">
      <p className="text-xs text-pipeline-400">{label}</p>
      <p className="font-semibold text-pipeline-700 capitalize">{value}</p>
    </div>
  );
}
