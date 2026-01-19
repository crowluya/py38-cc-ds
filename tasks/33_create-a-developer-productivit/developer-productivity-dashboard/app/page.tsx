'use client';

import { useState } from 'react';
import { useAnalysisStore } from '@/lib/store';
import { RepositoryInput } from '@/components/RepositoryInput';
import { MetricCard } from '@/components/metrics/MetricCard';
import { CommitFrequencyChart } from '@/components/charts/CommitFrequencyChart';
import { LanguageDistributionChart } from '@/components/charts/LanguageDistributionChart';
import { HourlyActivityHeatmap } from '@/components/charts/HourlyActivityHeatmap';
import { VelocityChart } from '@/components/charts/VelocityChart';
import { TopContributors } from '@/components/metrics/TopContributors';
import { TopFiles } from '@/components/metrics/TopFiles';
import { InsightsPanel } from '@/components/InsightsPanel';
import { GitCommit, Users, Code2, Activity } from 'lucide-react';

export default function Home() {
  const { repository, metrics, isLoading, error, setRepository, setMetrics, setLoading, setError, clearAnalysis } = useAnalysisStore();

  const handleAnalyze = async (repoPath: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repoPath }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze repository');
      }

      const data = await response.json();
      setRepository(data.repository);
      setMetrics(data.metrics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Developer Productivity Dashboard
              </h1>
              <p className="text-sm text-gray-600">
                Analyze your Git repositories for insights on coding patterns
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Repository Input */}
        <div className="mb-8">
          <RepositoryInput onAnalyze={handleAnalyze} isLoading={isLoading} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Dashboard */}
        {metrics && repository && (
          <div className="space-y-8">
            {/* Repository Info */}
            <div className="bg-white rounded-lg p-6 border border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                {repository.name}
              </h2>
              <p className="text-sm text-gray-600">
                Branch: <span className="font-medium">{repository.branch}</span>
                {' · '}Path: <span className="font-mono text-xs">{repository.path}</span>
              </p>
            </div>

            {/* Summary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Commits"
                value={metrics.totalCommits.toLocaleString()}
                icon={GitCommit}
                description="All time commits"
              />
              <MetricCard
                title="Contributors"
                value={metrics.totalAuthors}
                icon={Users}
                description="Active developers"
              />
              <MetricCard
                title="Languages"
                value={metrics.languageDistribution.length}
                icon={Code2}
                description="Programming languages used"
              />
              <MetricCard
                title="Avg Daily Velocity"
                value={
                  metrics.velocity.length > 0
                    ? (metrics.totalCommits / Math.max(metrics.velocity.length, 1)).toFixed(1)
                    : '0'
                }
                icon={Activity}
                description="Commits per day"
              />
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CommitFrequencyChart data={metrics.commitFrequency} />
              <LanguageDistributionChart data={metrics.languageDistribution} />
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <HourlyActivityHeatmap data={metrics.hourlyActivity} />
              <VelocityChart data={metrics.velocity} />
            </div>

            {/* Contributors and Files */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TopContributors data={metrics.topContributors} />
              <TopFiles data={metrics.topFiles} />
            </div>

            {/* Insights */}
            <InsightsPanel metrics={metrics} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-600">
            Developer Productivity Dashboard · Built with Next.js
          </p>
        </div>
      </footer>
    </div>
  );
}
