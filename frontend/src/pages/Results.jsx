import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import ResultCard from '../components/ResultCard';
import ImageViewer from '../components/ImageViewer';
import FeatureTable from '../components/FeatureTable';
import MetricsTable from '../components/MetricsTable';
import ComparisonChart from '../components/ComparisonChart';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { getResults, getComparison } from '../services/api';

export default function Results() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const imageId = searchParams.get('imageId');

  const [resultData,  setResultData]  = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [isLoading,   setIsLoading]   = useState(false);
  const [error,       setError]       = useState('');

  const fetchData = async () => {
    if (!imageId) return;
    setIsLoading(true);
    setError('');

    try {
      const [resResult, resCompare] = await Promise.all([
        getResults(imageId),
        getComparison(),
      ]);
      setResultData(resResult?.data ?? resResult);
      setCompareData(resCompare?.data ?? resCompare);
    } catch (err) {
      setError(err.message || 'Failed to load results.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageId]);

  // ── No imageId — prompt user ─────────────────────────────────────────────
  if (!imageId) {
    return (
      <Layout>
        <div className="max-w-3xl mx-auto">
          <div className="card text-center py-16 space-y-4">
            <svg className="w-14 h-14 mx-auto text-pipeline-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <p className="text-pipeline-600 font-medium">No image selected</p>
            <p className="text-pipeline-400 text-sm">Upload and detect an MRI image first to view results here.</p>
            <Button variant="primary" onClick={() => navigate('/detect')}>
              Go to Detection
            </Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-pipeline-900">Analysis Results</h1>
            <p className="text-pipeline-400 text-xs mt-1 font-mono">Image ID: {imageId}</p>
          </div>
          <Button variant="secondary" onClick={() => navigate('/detect')}>
            ← New Detection
          </Button>
        </div>

        {/* Loading */}
        {isLoading && <LoadingSpinner variant="card" message="Loading results..." size="lg" />}

        {/* Error */}
        {error && <ErrorMessage message={error} onRetry={fetchData} />}

        {/* Results */}
        {!isLoading && !error && resultData && (
          <div className="space-y-6">

            {/* 1. Classification result */}
            <ResultCard
              prediction={resultData.result?.prediction ?? resultData.prediction}
              confidence={resultData.result?.confidence ?? resultData.confidence}
            />

            {/* 2. Pipeline images */}
            <div className="card">
              <h2 className="section-title">Pipeline Images</h2>
              <ImageViewer paths={resultData.paths ?? {}} />
            </div>

            {/* 3. GLCM features */}
            <div className="card">
              <h2 className="section-title">Extracted GLCM Features</h2>
              <FeatureTable features={resultData.features} />
            </div>

            {/* 4. Evaluation metrics */}
            <div className="card">
              <h2 className="section-title">Evaluation Metrics</h2>
              <MetricsTable metrics={resultData.metrics} />
            </div>

            {/* 5. Comparison charts */}
            {compareData && (
              <div>
                <h2 className="section-title px-0 mb-4">Model Comparison (Figures 9–14)</h2>
                <ComparisonChart compareData={compareData} />
              </div>
            )}

          </div>
        )}

      </div>
    </Layout>
  );
}
