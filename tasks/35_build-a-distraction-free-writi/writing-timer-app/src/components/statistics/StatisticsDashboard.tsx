import React from 'react';
import { useStats } from '../../hooks/useStats';
import { formatDuration } from '../../utils/time';
import { StatsCard } from './StatsCard';
import { StreakDisplay } from './StreakDisplay';

export function StatisticsDashboard() {
  const { statistics, loading } = useStats();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!statistics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">No statistics available yet.</p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
          Start a writing session to track your progress!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Today's Stats */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          Today's Progress
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatsCard
            title="Focus Time"
            value={formatDuration(statistics.today.focusTime)}
            icon="⏱️"
            color="blue"
          />
          <StatsCard
            title="Sessions"
            value={statistics.today.sessions}
            icon="📝"
            color="purple"
          />
          <StatsCard
            title="Daily Goal"
            value={`${Math.round(statistics.today.goalProgress * 100)}%`}
            subtitle="Completed"
            icon="🎯"
            color="green"
          />
        </div>
      </div>

      {/* Streak */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          Habit Building
        </h2>
        <StreakDisplay
          currentStreak={statistics.overall.currentStreak}
          longestStreak={statistics.overall.longestStreak}
        />
      </div>

      {/* Weekly Stats */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          This Week
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatsCard
            title="Focus Time"
            value={formatDuration(statistics.week.focusTime)}
            subtitle={`${statistics.week.days} days active`}
            icon="📊"
            color="blue"
          />
          <StatsCard
            title="Sessions"
            value={statistics.week.sessions}
            subtitle="Total sessions"
            icon="✍️"
            color="purple"
          />
        </div>
      </div>

      {/* Monthly Stats */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          This Month
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatsCard
            title="Focus Time"
            value={formatDuration(statistics.month.focusTime)}
            subtitle={`${statistics.month.days} days active`}
            icon="📈"
            color="blue"
          />
          <StatsCard
            title="Sessions"
            value={statistics.month.sessions}
            subtitle="Total sessions"
            icon="📚"
            color="purple"
          />
        </div>
      </div>

      {/* Overall Stats */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          All Time
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatsCard
            title="Total Focus Time"
            value={formatDuration(statistics.overall.totalFocusTime)}
            subtitle="Since you started"
            icon="⏰"
            color="orange"
          />
          <StatsCard
            title="Total Sessions"
            value={statistics.overall.totalSessions}
            subtitle="Completed sessions"
            icon="🏆"
            color="green"
          />
        </div>
      </div>

      {/* Motivational Message */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <p className="text-center text-blue-800 dark:text-blue-200 font-medium">
          {statistics.overall.currentStreak >= 30
            ? `Amazing! You've maintained a ${statistics.overall.currentStreak}-day streak! 🌟`
            : statistics.overall.currentStreak >= 7
            ? `Great job! ${statistics.overall.currentStreak} days in a row! Keep it up! 💪`
            : statistics.today.sessions > 0
            ? "You're building a great habit! Every session counts! 📖"
            : "Ready to start? Begin your writing journey today! ✍️"}
        </p>
      </div>
    </div>
  );
}
