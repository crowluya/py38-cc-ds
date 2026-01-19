import React, { useState, useEffect } from 'react';
import { useTimer } from '../../hooks/useTimer';
import { TimerDisplay } from './TimerDisplay';
import { TimerControls } from './TimerControls';
import { DurationSelector } from './DurationSelector';
import { db } from '../../db/dexie';

export function TimerContainer() {
  const [duration, setDuration] = useState(1500); // Default 25 minutes
  const [sessionType, setSessionType] = useState<'focus' | 'break'>('focus');
  const [settings, setSettings] = useState<any>(null);

  const { timerState, startSession, pauseTimer, resumeTimer, stopTimer, resetTimer } =
    useTimer({
      onComplete: async () => {
        // Play notification sound
        if (settings?.enableSound) {
          // TODO: Play sound
        }

        // Show notification
        if (settings?.enableNotifications && Notification.permission === 'granted') {
          new Notification('Session Complete!', {
            body: sessionType === 'focus' ? 'Time for a break!' : 'Ready to focus again?',
            icon: '/icon-192.png',
          });
        }

        // Auto-start break if enabled
        if (sessionType === 'focus' && settings?.autoStartBreaks) {
          const breakDuration = settings.defaultShortBreak || 300;
          setSessionType('break');
          setDuration(breakDuration);
          setTimeout(() => {
            startSession(breakDuration, 'break');
          }, 2000);
        }
      },
    });

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      const savedSettings = await db.settings.get(1);
      setSettings(savedSettings);
      if (savedSettings) {
        setDuration(savedSettings.defaultFocusDuration);
      }
    };
    loadSettings();
  }, []);

  // Request notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const handleStart = () => {
    startSession(duration, sessionType);
  };

  const handleStop = async () => {
    stopTimer();
    setSessionType('focus');
  };

  const handleReset = () => {
    resetTimer();
    setSessionType('focus');
    if (settings) {
      setDuration(settings.defaultFocusDuration);
    }
  };

  return (
    <div className="flex flex-col items-center gap-8 p-8">
      {/* Session Type Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setSessionType('focus')}
          disabled={timerState.isActive}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            sessionType === 'focus' && !timerState.isActive
              ? 'bg-blue-500 text-white shadow-lg'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
          } disabled:opacity-50`}
        >
          Focus
        </button>
        <button
          onClick={() => setSessionType('break')}
          disabled={timerState.isActive}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            sessionType === 'break' && !timerState.isActive
              ? 'bg-green-500 text-white shadow-lg'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
          } disabled:opacity-50`}
        >
          Break
        </button>
      </div>

      {/* Duration Selector */}
      {!timerState.isActive && (
        <DurationSelector
          value={duration}
          onChange={setDuration}
          presets={
            sessionType === 'focus'
              ? [
                  { label: '15 min', value: 900 },
                  { label: '25 min', value: 1500 },
                  { label: '45 min', value: 2700 },
                  { label: '60 min', value: 3600 },
                  { label: '90 min', value: 5400 },
                ]
              : [
                  { label: '5 min', value: 300 },
                  { label: '10 min', value: 600 },
                  { label: '15 min', value: 900 },
                  { label: '20 min', value: 1200 },
                ]
          }
        />
      )}

      {/* Timer Display */}
      <TimerDisplay
        timeLeft={timerState.timeLeft}
        duration={timerState.duration}
        isActive={timerState.isActive}
        isPaused={timerState.isPaused}
        isBreak={timerState.isBreak}
      />

      {/* Timer Controls */}
      <TimerControls
        isActive={timerState.isActive}
        isPaused={timerState.isPaused}
        onStart={handleStart}
        onPause={pauseTimer}
        onResume={resumeTimer}
        onStop={handleStop}
        onReset={handleReset}
      />
    </div>
  );
}
