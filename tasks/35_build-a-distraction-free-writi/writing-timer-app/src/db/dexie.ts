import Dexie, { type Table } from 'dexie';
import type {
  Session,
  Settings,
  DailyStats,
  WritingContent,
  Milestone,
} from '../types';

export class WritingTimerDB extends Dexie {
  sessions!: Table<Session>;
  settings!: Table<Settings>;
  dailyStats!: Table<DailyStats>;
  writingContent!: Table<WritingContent>;
  milestones!: Table<Milestone>;

  constructor() {
    super('WritingTimerDB');

    // Version 1 - Initial schema
    this.version(1).stores({
      sessions: '++id, startTime, type, status',
      settings: 'id',
      dailyStats: '++id, date',
      writingContent: '++id, sessionId',
      milestones: '++id, type, achievedAt',
    });

    // Version 2 - Add compound indexes
    this.version(2).stores({
      sessions: '++id, startTime, type, status, [startTime+type]',
      settings: 'id',
      dailyStats: '++id, date, streakDay, totalFocusTime',
      writingContent: '++id, sessionId, savedAt',
      milestones: '++id, type, achievedAt, [type+acknowledged]',
    }).upgrade(async (tx) => {
      // Migration logic if needed
      const sessions = await tx.table('sessions').toArray();
      for (const session of sessions) {
        if (session.wordsWritten === undefined) {
          await tx.table('sessions').update(session.id!, { wordsWritten: 0 });
        }
      }
    });
  }

  // Initialize default settings
  async initializeSettings(): Promise<void> {
    const settingsCount = await this.settings.count();
    if (settingsCount === 0) {
      const defaultSettings: Settings = {
        id: 1,
        defaultFocusDuration: 1500, // 25 minutes
        defaultShortBreak: 300, // 5 minutes
        defaultLongBreak: 900, // 15 minutes
        autoStartBreaks: false,
        autoStartSessions: false,
        enableNotifications: true,
        enableSound: true,
        soundVolume: 0.5,
        notificationSound: 'chime.mp3',
        theme: 'sepia',
        fontSize: 'medium',
        fontFamily: 'serif',
        autoSaveInterval: 30,
        showWordCount: false,
        enableFullscreen: true,
        dailyGoalMinutes: 60,
        dailyGoalWords: 500,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      await this.settings.add(defaultSettings);
    }
  }

  // Get or create daily stats for a date
  async getOrCreateDailyStats(date: string): Promise<DailyStats> {
    let stats = await this.dailyStats.where('date').equals(date).first();

    if (!stats) {
      const prevStats = await this.dailyStats
        .where('date')
        .below(date)
        .reverse()
        .first();

      stats = {
        date,
        totalFocusTime: 0,
        totalBreakTime: 0,
        sessionCount: 0,
        wordsWritten: 0,
        longestSession: 0,
        streakDay: (prevStats?.streakDay ?? 0) + 1,
        goalMinutesProgress: 0,
        goalWordsProgress: 0,
        goalsMet: false,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      await this.dailyStats.add(stats);
    }

    return stats;
  }
}

export const db = new WritingTimerDB();

// Initialize database
export async function initializeDatabase(): Promise<void> {
  await db.open();
  await db.initializeSettings();
}
