import React from 'react';
import { formatTime } from '../../utils/time';

interface TimerDisplayProps {
  timeLeft: number;
  duration: number;
  isActive: boolean;
  isPaused: boolean;
  isBreak: boolean;
}

export function TimerDisplay({
  timeLeft,
  duration,
  isActive,
  isPaused,
  isBreak,
}: TimerDisplayProps) {
  const progress = duration > 0 ? ((duration - timeLeft) / duration) * 100 : 0;
  const circumference = 2 * Math.PI * 120; // Radius of 120
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      {/* Circular Progress */}
      <div className="relative w-72 h-72">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 250 250">
          {/* Background circle */}
          <circle
            cx="125"
            cy="125"
            r="120"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Progress circle */}
          <circle
            cx="125"
            cy="125"
            r="120"
            stroke={isBreak ? 'currentColor' : 'currentColor'}
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`transition-all duration-1000 ease-linear ${
              isBreak
                ? 'text-green-500 dark:text-green-400'
                : 'text-blue-500 dark:text-blue-400'
            }`}
          />
        </svg>

        {/* Time Display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-6xl font-bold text-gray-800 dark:text-gray-100 tabular-nums">
            {formatTime(timeLeft)}
          </div>

          {/* Status Indicator */}
          <div className="mt-2 flex items-center gap-2">
            {isActive && !isPaused && (
              <div className="flex items-center gap-2">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {isBreak ? 'Break' : 'Focus'}
                </span>
              </div>
            )}

            {isActive && isPaused && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">⏸ Paused</span>
              </div>
            )}

            {!isActive && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Ready</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Progress Text */}
      {isActive && (
        <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
          {Math.round(progress)}% complete
        </div>
      )}
    </div>
  );
}
