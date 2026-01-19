'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GitMetrics } from '@/lib/git/types';
import { Lightbulb, TrendingUp, AlertCircle, Clock } from 'lucide-react';

interface InsightsPanelProps {
  metrics: GitMetrics;
}

export function InsightsPanel({ metrics }: InsightsPanelProps) {
  const insights = generateInsights(metrics);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          Insights & Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {insights.map((insight, index) => (
            <div key={index} className="flex gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="flex-shrink-0">
                {insight.type === 'trend' && <TrendingUp className="w-5 h-5 text-blue-500" />}
                {insight.type === 'warning' && <AlertCircle className="w-5 h-5 text-orange-500" />}
                {insight.type === 'info' && <Clock className="w-5 h-5 text-green-500" />}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{insight.title}</p>
                <p className="text-sm text-gray-600 mt-1">{insight.description}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function generateInsights(metrics: GitMetrics) {
  const insights: {
    type: 'trend' | 'warning' | 'info';
    title: string;
    description: string;
  }[] = [];

  // Team size insight
  if (metrics.totalAuthors === 1) {
    insights.push({
      type: 'info',
      title: 'Solo Project',
      description: 'This appears to be a personal project with a single contributor.',
    });
  } else if (metrics.totalAuthors > 10) {
    insights.push({
      type: 'trend',
      title: 'Large Team',
      description: `This project has ${metrics.totalAuthors} contributors. Consider establishing clear contribution guidelines.`,
    });
  }

  // Language diversity
  if (metrics.languageDistribution.length > 5) {
    insights.push({
      type: 'info',
      title: 'Polyglot Repository',
      description: `This project uses ${metrics.languageDistribution.length} different programming languages.`,
    });
  }

  // Top language
  const topLanguage = metrics.languageDistribution[0];
  if (topLanguage && topLanguage.percentage > 80) {
    insights.push({
      type: 'trend',
      title: `${topLanguage.language}-Focused`,
      description: `${topLanguage.percentage.toFixed(1)}% of the codebase is written in ${topLanguage.language}.`,
    });
  }

  // Activity patterns
  const totalCommits = metrics.totalCommits;
  if (totalCommits > 1000) {
    insights.push({
      type: 'trend',
      title: 'Active Repository',
      description: `This repository has ${totalCommits.toLocaleString()} commits, showing sustained development activity.`,
    });
  }

  // Peak hours
  const hourlyData = metrics.hourlyActivity;
  const maxActivity = hourlyData.reduce((max, curr) =>
    curr.count > max.count ? curr : max
  , hourlyData[0]);

  if (maxActivity && maxActivity.count > 0) {
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    insights.push({
      type: 'info',
      title: 'Peak Productivity Time',
      description: `Most active on ${dayNames[maxActivity.day]} around ${maxActivity.hour}:00.`,
    });
  }

  // Velocity insight
  if (metrics.velocity.length > 0) {
    const recentVelocity = metrics.velocity.slice(-7);
    const avgCommits = recentVelocity.reduce((sum, v) => sum + v.commits, 0) / recentVelocity.length;
    const avgLines = recentVelocity.reduce((sum, v) => sum + v.lines, 0) / recentVelocity.length;

    if (avgCommits > 10) {
      insights.push({
        type: 'trend',
        title: 'High Velocity',
        description: `Averaging ${avgCommits.toFixed(1)} commits per day recently.`,
      });
    }
  }

  return insights;
}
