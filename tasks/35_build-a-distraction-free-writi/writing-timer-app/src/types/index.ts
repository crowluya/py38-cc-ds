// Core Types for Writing Timer App

export type SessionType = 'focus' | 'break';
export type SessionStatus = 'completed' | 'stopped' | 'in-progress';
export type Theme = 'light' | 'dark' | 'sepia';
export type FontSize = 'small' | 'medium' | 'large';
export type FontFamily = 'serif' | 'sans' | 'mono';

export interface Session {
  id?: number;
  startTime: number;
  endTime?: number;
  duration: number;
  actualDuration?: number;
  type: SessionType;
  status: SessionStatus;
  wordsWritten?: number;
  notes?: string;
  createdAt: number;
  updatedAt: number;
}

export interface Settings {
  id: number;
  // Timer Settings
  defaultFocusDuration: number;
  defaultShortBreak: number;
  defaultLongBreak: number;
  autoStartBreaks: boolean;
  autoStartSessions: boolean;

  // Notification Settings
  enableNotifications: boolean;
  enableSound: boolean;
  soundVolume: number;
  notificationSound: string;

  // Appearance Settings
  theme: Theme;
  fontSize: FontSize;
  fontFamily: FontFamily;

  // Writing Settings
  autoSaveInterval: number;
  showWordCount: boolean;
  enableFullscreen: boolean;

  // Goals
  dailyGoalMinutes: number;
  dailyGoalWords: number;

  // Metadata
  createdAt: number;
  updatedAt: number;
}

export interface DailyStats {
  id?: number;
  date: string;
  totalFocusTime: number;
  totalBreakTime: number;
  sessionCount: number;
  wordsWritten: number;
  longestSession: number;
  streakDay: number;
  goalMinutesProgress: number;
  goalWordsProgress: number;
  goalsMet: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface WritingContent {
  id?: number;
  sessionId?: number;
  content: string;
  wordCount: number;
  characterCount: number;
  savedAt: number;
  createdAt: number;
  updatedAt: number;
}

export type MilestoneType = 'streak' | 'total-time' | 'words' | 'sessions';

export interface Milestone {
  id?: number;
  type: MilestoneType;
  value: number;
  achievedAt: number;
  acknowledged: boolean;
  title: string;
  description: string;
  createdAt: number;
}

export interface TimerState {
  isActive: boolean;
  isPaused: boolean;
  isBreak: boolean;
  timeLeft: number;
  duration: number;
  sessionStartTime: number;
  currentSession?: Session;
}

export interface Statistics {
  today: {
    focusTime: number;
    breakTime: number;
    sessions: number;
    words: number;
    goalProgress: number;
  };
  week: {
    focusTime: number;
    sessions: number;
    days: number;
  };
  month: {
    focusTime: number;
    sessions: number;
    days: number;
  };
  overall: {
    totalFocusTime: number;
    totalSessions: number;
    currentStreak: number;
    longestStreak: number;
    totalWords: number;
  };
}

export interface ExportData {
  version: number;
  exportedAt: number;
  data: {
    sessions: Session[];
    settings: Settings;
    dailyStats: DailyStats[];
    milestones: Milestone[];
  };
}
