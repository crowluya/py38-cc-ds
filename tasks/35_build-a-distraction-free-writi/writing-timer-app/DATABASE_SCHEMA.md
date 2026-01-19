# Database Schema Design

## Overview
Using **IndexedDB** via **Dexie.js** for persistent local storage of writing sessions, statistics, and user settings.

## Database: WritingTimerDB

### Tables

#### 1. sessions
Stores completed and in-progress writing sessions.

```typescript
interface Session {
  id: number;                    // Auto-increment primary key
  startTime: number;             // Unix timestamp (ms)
  endTime?: number;              // Unix timestamp (ms) - null if in progress
  duration: number;              // Planned duration in seconds
  actualDuration?: number;       // Actual duration in seconds
  type: 'focus' | 'break';       // Session type
  status: 'completed' | 'stopped' | 'in-progress';
  wordsWritten?: number;         // Optional word count
  notes?: string;                // Optional session notes
  createdAt: number;             // Unix timestamp (ms)
  updatedAt: number;             // Unix timestamp (ms)
}
```

**Indexes:**
- `startTime` - For date range queries
- `type` - For filtering session types
- `status` - For filtering active/completed sessions
- `[startTime+type]` - Compound index for statistics

#### 2. settings
Stores user preferences and application settings.

```typescript
interface Settings {
  id: number;                    // Always 1 (singleton)
  // Timer Settings
  defaultFocusDuration: number;  // Default focus duration (seconds)
  defaultShortBreak: number;     // Default short break (seconds)
  defaultLongBreak: number;      // Default long break (seconds)
  autoStartBreaks: boolean;      // Auto-start breaks after focus
  autoStartSessions: boolean;    // Auto-start next session

  // Notification Settings
  enableNotifications: boolean;  // Enable browser notifications
  enableSound: boolean;          // Enable sound alerts
  soundVolume: number;           // Volume (0.0 - 1.0)
  notificationSound: string;     // Sound file name

  // Appearance Settings
  theme: 'light' | 'dark' | 'sepia';
  fontSize: 'small' | 'medium' | 'large';
  fontFamily: 'serif' | 'sans' | 'mono';

  // Writing Settings
  autoSaveInterval: number;      // Auto-save interval (seconds)
  showWordCount: boolean;        // Show word count while writing
  enableFullscreen: boolean;     // Allow fullscreen mode

  // Goals
  dailyGoalMinutes: number;      // Daily writing goal (minutes)
  dailyGoalWords: number;        // Daily word count goal

  // Metadata
  createdAt: number;
  updatedAt: number;
}
```

#### 3. dailyStats
Aggregated daily statistics for quick access.

```typescript
interface DailyStats {
  id: number;                    // Auto-increment
  date: string;                  // ISO date string (YYYY-MM-DD)
  totalFocusTime: number;        // Total focus time (seconds)
  totalBreakTime: number;        // Total break time (seconds)
  sessionCount: number;          // Number of sessions completed
  wordsWritten: number;          // Total words written
  longestSession: number;        // Longest session duration (seconds)
  streakDay: number;             // Consecutive day count

  // Goal progress
  goalMinutesProgress: number;   // Progress toward daily time goal (0-1)
  goalWordsProgress: number;     // Progress toward daily word goal (0-1)
  goalsMet: boolean;             // Were daily goals met?

  createdAt: number;
  updatedAt: number;
}
```

**Indexes:**
- `date` - Unique, for daily lookups
- `streakDay` - For sorting by streaks
- `totalFocusTime` - For finding most productive days

#### 4. writingContent
Auto-saved writing content (optional feature).

```typescript
interface WritingContent {
  id: number;                    // Auto-increment
  sessionId?: number;            // Associated session (foreign key)
  content: string;               // Text content
  wordCount: number;             // Calculated word count
  characterCount: number;        // Character count
  savedAt: number;               // Unix timestamp (ms)

  // Metadata
  createdAt: number;
  updatedAt: number;
}
```

**Indexes:**
- `sessionId` - For retrieving content by session
- `savedAt` - For finding recent content

#### 5. milestones
Tracks user achievements and milestones.

```typescript
interface Milestone {
  id: number;                    // Auto-increment
  type: 'streak' | 'total-time' | 'words' | 'sessions';
  value: number;                 // Milestone value (e.g., 30 days)
  achievedAt: number;            // Unix timestamp (ms)
  acknowledged: boolean;         // Has user seen this milestone?

  // Display info
  title: string;                 // e.g., "30-Day Streak"
  description: string;           // e.g., "You've written for 30 consecutive days!"

  createdAt: number;
}
```

**Indexes:**
- `type` - For filtering milestone types
- `achievedAt` - For sorting by achievement date
- `[type+acknowledged]` - For unacknowledged milestones

## Relationships

```
sessions (1) ←→ (many) writingContent
  └─ sessionId foreign key

sessions (1) → (1) dailyStats
  └─ Aggregated by date

milestones (standalone)
  └─ Derived from sessions data
```

## Data Flow

### Starting a Session
1. Create new `session` record with `status: 'in-progress'`
2. Save to IndexedDB
3. Start timer

### During a Session
1. Update `WritingContent` every 30 seconds (auto-save)
2. Update current session in state (not DB yet)

### Completing a Session
1. Update `session` record with `endTime`, `actualDuration`, `status: 'completed'`
2. Create/update `DailyStats` for the session's date
3. Check for new `Milestones`
4. Save all changes to IndexedDB

### Statistics Calculation
1. Query `sessions` by date range
2. Aggregate data (sum duration, count sessions, etc.)
3. Update or create `DailyStats` records
4. Calculate streaks from consecutive daily stats

## Default Settings

```typescript
const defaultSettings: Settings = {
  id: 1,
  defaultFocusDuration: 1500,    // 25 minutes (Pomodoro)
  defaultShortBreak: 300,        // 5 minutes
  defaultLongBreak: 900,         // 15 minutes
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

  dailyGoalMinutes: 60,          // 1 hour
  dailyGoalWords: 500,           // 500 words

  createdAt: Date.now(),
  updatedAt: Date.now(),
}
```

## Query Patterns

### Get Today's Sessions
```typescript
const today = new Date().toISOString().split('T')[0];
const sessions = await db.sessions
  .where('startTime')
  .above(startOfDay)
  .below(endOfDay)
  .toArray();
```

### Get Current Streak
```typescript
const stats = await db.dailyStats
  .where('date')
  .belowOrEqual(today)
  .reverse()
  .until(stat => !stat.goalsMet)
  .toArray();
return stats.length;
```

### Get Last 7 Days Statistics
```typescript
const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
const stats = await db.dailyStats
  .where('date')
  .above(formatDate(sevenDaysAgo))
  .toArray();
```

### Get Total Writing Time
```typescript
const sessions = await db.sessions
  .where('type')
  .equals('focus')
  .toArray();
const totalTime = sessions.reduce((sum, s) => sum + (s.actualDuration || 0), 0);
```

## Data Migration Strategy

### Version 1 → Version 2 (Example)
```typescript
db.version(1).stores({
  sessions: '++id, startTime, type, status',
  settings: 'id',
});

db.version(2).stores({
  sessions: '++id, startTime, type, status, [startTime+type]',
  settings: 'id',
  dailyStats: '++id, date, streakDay, totalFocusTime',
  writingContent: '++id, sessionId, savedAt',
  milestones: '++id, type, achievedAt, [type+acknowledged]',
}).upgrade(tx => {
  // Migrate existing data
  return tx.table('sessions').toCollection().modify(session => {
    if (!session.wordsWritten) {
      session.wordsWritten = 0;
    }
  });
});
```

## Performance Optimization

### Indexing Strategy
- Index all frequently queried fields
- Use compound indexes for common query patterns
- Avoid over-indexing (slows writes)

### Query Optimization
- Use `limit()` for large result sets
- Paginate session history (50 per page)
- Cache calculated statistics in `dailyStats`

### Storage Optimization
- Don't store full text content by default (optional feature)
- Clean up old content (keep last 30 days)
- Compact database periodically

## Backup & Export

### Export Format
```json
{
  "version": 2,
  "exportedAt": 1705708800000,
  "data": {
    "sessions": [...],
    "settings": {...},
    "dailyStats": [...],
    "milestones": [...]
  }
}
```

### Import Process
1. Validate JSON structure
2. Check version compatibility
3. Merge with existing data (user choice)
4. Update indexes
5. Recalculate statistics

## Privacy & Security

### Data Protection
- All data stored locally (no server transmission)
- No personal identifiers required
- User has full control over data

### Data Deletion
```typescript
async function clearAllData() {
  await db.sessions.clear();
  await db.dailyStats.clear();
  await db.writingContent.clear();
  await db.milestones.clear();
  // Keep settings
}
```

## Testing Strategy

### Unit Tests
- Test repository methods
- Test aggregation functions
- Test milestone calculations

### Integration Tests
- Test database operations
- Test migration logic
- Test export/import functionality

### Performance Tests
- Query performance with 1000+ sessions
- Write performance during active session
- Index effectiveness verification
