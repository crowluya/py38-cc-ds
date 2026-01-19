import React from 'react';

interface StreakDisplayProps {
  currentStreak: number;
  longestStreak: number;
}

export function StreakDisplay({ currentStreak, longestStreak }: StreakDisplayProps) {
  return (
    <div className="bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 rounded-lg p-6 border border-orange-200 dark:border-orange-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">🔥 Writing Streak</h3>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-4xl font-bold text-orange-600 dark:text-orange-400 mb-1">
            {currentStreak}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">Current Streak</p>
        </div>

        <div className="text-center">
          <div className="text-4xl font-bold text-amber-600 dark:text-amber-400 mb-1">
            {longestStreak}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">Longest Streak</p>
        </div>
      </div>

      {/* Streak Visualization */}
      <div className="mt-4">
        <div className="flex gap-1 justify-center">
          {Array.from({ length: 7 }).map((_, i) => (
            <div
              key={i}
              className={`w-8 h-8 rounded flex items-center justify-center text-xs font-medium ${
                i < currentStreak
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
              }`}
            >
              {i < 7 - currentStreak ? '' : i + 1}
            </div>
          ))}
        </div>
        <p className="text-xs text-center text-gray-500 dark:text-gray-400 mt-2">
          Last 7 days
        </p>
      </div>
    </div>
  );
}
