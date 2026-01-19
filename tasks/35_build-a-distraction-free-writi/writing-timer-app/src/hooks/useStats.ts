import { useState, useEffect } from 'react';
import { db } from '../db/dexie';
import type { Statistics } from '../types';
import { getTodayString, getLastNDays, getWeekRange, getMonthRange } from '../utils/time';

export function useStats() {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStatistics = async () => {
      try {
        const today = getTodayString();
        const last7Days = getLastNDays(7);
        const weekRange = getWeekRange();
        const monthRange = getMonthRange();

        // Today's sessions
        const todaySessions = await db.sessions
          .where('startTime')
          .between(last7Days.start, Date.now())
          .and(session => session.type === 'focus')
          .toArray();

        const todayFocusTime = todaySessions
          .filter(s => getTodayString() === new Date(s.startTime).toISOString().split('T')[0])
          .reduce((sum, s) => sum + (s.actualDuration || 0), 0);

        const todayBreakTime = todaySessions
          .filter(s => getTodayString() === new Date(s.startTime).toISOString().split('T')[0])
          .filter(s => s.type === 'break')
          .reduce((sum, s) => sum + (s.actualDuration || 0), 0);

        const todaySessionCount = todaySessions.filter(
          s => getTodayString() === new Date(s.startTime).toISOString().split('T')[0]
        ).length;

        // Weekly stats
        const weekSessions = await db.sessions
          .where('startTime')
          .between(weekRange.start, weekRange.end)
          .filter(s => s.type === 'focus')
          .toArray();

        const weekFocusTime = weekSessions.reduce((sum, s) => sum + (s.actualDuration || 0), 0);
        const weekSessionCount = weekSessions.length;

        // Get unique days with sessions
        const weekDays = new Set(
          weekSessions.map(s => new Date(s.startTime).toISOString().split('T')[0])
        ).size;

        // Monthly stats
        const monthSessions = await db.sessions
          .where('startTime')
          .between(monthRange.start, monthRange.end)
          .filter(s => s.type === 'focus')
          .toArray();

        const monthFocusTime = monthSessions.reduce((sum, s) => sum + (s.actualDuration || 0), 0);
        const monthSessionCount = monthSessions.length;

        const monthDays = new Set(
          monthSessions.map(s => new Date(s.startTime).toISOString().split('T')[0])
        ).size;

        // Overall stats
        const allSessions = await db.sessions
          .where('type')
          .equals('focus')
          .toArray();

        const totalFocusTime = allSessions.reduce((sum, s) => sum + (s.actualDuration || 0), 0);

        // Calculate streak
        const dailyStats = await db.dailyStats
          .orderBy('date')
          .reverse()
          .toArray();

        let currentStreak = 0;
        for (const stat of dailyStats) {
          if (stat.sessionCount > 0) {
            currentStreak++;
          } else {
            break;
          }
        }

        const longestStreak = Math.max(
          0,
          ...dailyStats.map(s => (s.sessionCount > 0 ? s.streakDay : 0))
        );

        const totalWords = allSessions.reduce((sum, s) => sum + (s.wordsWritten || 0), 0);

        // Get today's stats for goal progress
        const todayStats = await db.dailyStats.where('date').equals(today).first();
        const goalProgress = todayStats?.goalMinutesProgress || 0;

        setStatistics({
          today: {
            focusTime: todayFocusTime,
            breakTime: todayBreakTime,
            sessions: todaySessionCount,
            words: 0,
            goalProgress,
          },
          week: {
            focusTime: weekFocusTime,
            sessions: weekSessionCount,
            days: weekDays,
          },
          month: {
            focusTime: monthFocusTime,
            sessions: monthSessionCount,
            days: monthDays,
          },
          overall: {
            totalFocusTime,
            totalSessions: allSessions.length,
            currentStreak,
            longestStreak,
            totalWords,
          },
        });
      } catch (error) {
        console.error('Error loading statistics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStatistics();
  }, []);

  return { statistics, loading };
}
