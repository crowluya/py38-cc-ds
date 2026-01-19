/**
 * Format seconds to MM:SS or HH:MM:SS
 */
export function formatTime(seconds: number, showHours = false): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (showHours || hours > 0) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format seconds to human-readable duration (e.g., "25 min", "1 hr 30 min")
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0 && minutes > 0) {
    return `${hours} hr ${minutes} min`;
  } else if (hours > 0) {
    return `${hours} hr`;
  } else if (minutes > 0) {
    return `${minutes} min`;
  } else {
    return `${seconds} sec`;
  }
}

/**
 * Get start of day timestamp
 */
export function startOfDay(date: Date): number {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

/**
 * Get end of day timestamp
 */
export function endOfDay(date: Date): number {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return d.getTime();
}

/**
 * Format date to ISO date string (YYYY-MM-DD)
 */
export function formatDate(timestamp: number): string {
  return new Date(timestamp).toISOString().split('T')[0];
}

/**
 * Get today's date string
 */
export function getTodayString(): string {
  return formatDate(Date.now());
}

/**
 * Check if two dates are the same day
 */
export function isSameDay(timestamp1: number, timestamp2: number): boolean {
  return formatDate(timestamp1) === formatDate(timestamp2);
}

/**
 * Get days between two dates
 */
export function getDaysBetween(start: number, end: number): number {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Get date range for the last N days
 */
export function getLastNDays(days: number): { start: number; end: number } {
  const now = new Date();
  const end = endOfDay(now);
  const start = startOfDay(new Date(now.getTime() - (days - 1) * 24 * 60 * 60 * 1000));
  return { start, end };
}

/**
 * Get week start and end for a given date
 */
export function getWeekRange(date: Date = new Date()): { start: number; end: number } {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust to Monday
  const monday = new Date(d.setDate(diff));
  const sunday = new Date(d.setDate(diff + 6));

  return {
    start: startOfDay(monday),
    end: endOfDay(sunday),
  };
}

/**
 * Get month start and end for a given date
 */
export function getMonthRange(date: Date = new Date()): { start: number; end: number } {
  const d = new Date(date);
  const firstDay = new Date(d.getFullYear(), d.getMonth(), 1);
  const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0);

  return {
    start: startOfDay(firstDay),
    end: endOfDay(lastDay),
  };
}

/**
 * Format date for display (e.g., "Jan 19, 2026")
 */
export function formatDisplayDate(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format relative time (e.g., "2 hours ago", "today", "yesterday")
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 7) {
    return formatDisplayDate(timestamp);
  } else if (days > 1) {
    return `${days} days ago`;
  } else if (days === 1) {
    return 'yesterday';
  } else if (hours > 0) {
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
  } else if (minutes > 0) {
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
  } else {
    return 'just now';
  }
}
