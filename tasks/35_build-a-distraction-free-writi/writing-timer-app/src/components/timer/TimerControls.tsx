import React from 'react';

interface TimerControlsProps {
  isActive: boolean;
  isPaused: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  disabled?: boolean;
}

export function TimerControls({
  isActive,
  isPaused,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
  disabled = false,
}: TimerControlsProps) {
  return (
    <div className="flex items-center justify-center gap-4">
      {!isActive ? (
        <button
          onClick={onStart}
          disabled={disabled}
          className="px-8 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          Start Session
        </button>
      ) : (
        <>
          {!isPaused ? (
            <button
              onClick={onPause}
              className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105"
            >
              Pause
            </button>
          ) : (
            <button
              onClick={onResume}
              className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105"
            >
              Resume
            </button>
          )}

          <button
            onClick={onStop}
            className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105"
          >
            Stop
          </button>
        </>
      )}

      {!isActive && (
        <button
          onClick={onReset}
          className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105"
        >
          Reset
        </button>
      )}
    </div>
  );
}
