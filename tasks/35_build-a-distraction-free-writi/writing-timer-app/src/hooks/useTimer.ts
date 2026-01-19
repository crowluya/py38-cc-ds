import { useState, useEffect, useRef, useCallback } from 'react';
import type { TimerState, Session, SessionType } from '../types';
import { db } from '../db/dexie';

interface UseTimerOptions {
  onTick?: (timeLeft: number) => void;
  onComplete?: () => void;
  onSessionStart?: (session: Session) => void;
}

export function useTimer(options: UseTimerOptions = {}) {
  const [timerState, setTimerState] = useState<TimerState>({
    isActive: false,
    isPaused: false,
    isBreak: false,
    timeLeft: 0,
    duration: 0,
    sessionStartTime: 0,
  });

  const intervalRef = useRef<number | null>(null);
  const currentSessionRef = useRef<Session | undefined>(undefined);

  // Clear interval
  const clearInterval = () => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Start a new session
  const startSession = useCallback(async (duration: number, type: SessionType = 'focus') => {
    clearInterval();

    const now = Date.now();
    const session: Session = {
      startTime: now,
      duration,
      type,
      status: 'in-progress',
      createdAt: now,
      updatedAt: now,
    };

    // Save session to database
    const sessionId = await db.sessions.add(session);
    session.id = sessionId;
    currentSessionRef.current = session;

    setTimerState({
      isActive: true,
      isPaused: false,
      isBreak: type === 'break',
      timeLeft: duration,
      duration,
      sessionStartTime: now,
      currentSession: session,
    });

    options.onSessionStart?.(session);

    // Start timer
    intervalRef.current = window.setInterval(async () => {
      const currentTime = Date.now();
      const elapsed = Math.floor((currentTime - now) / 1000);
      const timeLeft = Math.max(0, duration - elapsed);

      setTimerState(prev => ({
        ...prev,
        timeLeft,
      }));

      options.onTick?.(timeLeft);

      // Timer complete
      if (timeLeft <= 0) {
        clearInterval();

        const endTime = Date.now();
        const actualDuration = Math.floor((endTime - now) / 1000);

        // Update session in database
        await db.sessions.update(sessionId!, {
          endTime,
          actualDuration,
          status: 'completed',
          updatedAt: endTime,
        });

        // Update daily stats
        const today = new Date().toISOString().split('T')[0];
        const stats = await db.getOrCreateDailyStats(today);

        if (type === 'focus') {
          await db.dailyStats.update(stats.id!, {
            totalFocusTime: stats.totalFocusTime + actualDuration,
            sessionCount: stats.sessionCount + 1,
            longestSession: Math.max(stats.longestSession, actualDuration),
            updatedAt: endTime,
          });
        } else {
          await db.dailyStats.update(stats.id!, {
            totalBreakTime: stats.totalBreakTime + actualDuration,
            updatedAt: endTime,
          });
        }

        setTimerState(prev => ({
          ...prev,
          isActive: false,
          isPaused: false,
          timeLeft: 0,
        }));

        options.onComplete?.();
      }
    }, 1000);
  }, [options]);

  // Pause the timer
  const pauseTimer = useCallback(() => {
    if (timerState.isActive && !timerState.isPaused) {
      clearInterval();
      setTimerState(prev => ({
        ...prev,
        isPaused: true,
      }));
    }
  }, [timerState.isActive, timerState.isPaused]);

  // Resume the timer
  const resumeTimer = useCallback(() => {
    if (timerState.isActive && timerState.isPaused) {
      const elapsed = Date.now() - timerState.sessionStartTime;

      intervalRef.current = window.setInterval(async () => {
        const currentTime = Date.now();
        const totalElapsed = Math.floor((currentTime - timerState.sessionStartTime) / 1000);
        const timeLeft = Math.max(0, timerState.duration - totalElapsed);

        setTimerState(prev => ({
          ...prev,
          timeLeft,
        }));

        options.onTick?.(timeLeft);

        if (timeLeft <= 0) {
          clearInterval();
          const endTime = Date.now();
          const actualDuration = totalElapsed;

          if (currentSessionRef.current?.id) {
            await db.sessions.update(currentSessionRef.current.id, {
              endTime,
              actualDuration,
              status: 'completed',
              updatedAt: endTime,
            });
          }

          setTimerState(prev => ({
            ...prev,
            isActive: false,
            isPaused: false,
            timeLeft: 0,
          }));

          options.onComplete?.();
        }
      }, 1000);

      setTimerState(prev => ({
        ...prev,
        isPaused: false,
      }));
    }
  }, [timerState, options]);

  // Stop the timer
  const stopTimer = useCallback(async () => {
    clearInterval();

    if (currentSessionRef.current?.id) {
      const endTime = Date.now();
      const actualDuration = Math.floor((endTime - timerState.sessionStartTime) / 1000);

      await db.sessions.update(currentSessionRef.current.id, {
        endTime,
        actualDuration,
        status: 'stopped',
        updatedAt: endTime,
      });
    }

    currentSessionRef.current = undefined;

    setTimerState({
      isActive: false,
      isPaused: false,
      isBreak: false,
      timeLeft: 0,
      duration: 0,
      sessionStartTime: 0,
    });
  }, [timerState.sessionStartTime]);

  // Reset the timer
  const resetTimer = useCallback(() => {
    clearInterval();
    currentSessionRef.current = undefined;

    setTimerState({
      isActive: false,
      isPaused: false,
      isBreak: false,
      timeLeft: 0,
      duration: 0,
      sessionStartTime: 0,
    });
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearInterval();
    };
  }, []);

  return {
    timerState,
    startSession,
    pauseTimer,
    resumeTimer,
    stopTimer,
    resetTimer,
  };
}
