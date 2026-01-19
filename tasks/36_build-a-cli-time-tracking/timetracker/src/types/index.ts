/**
 * Core data model types for the time tracker
 */

export interface TimeEntry {
  id: string;
  start_time: number; // Unix timestamp
  end_time?: number; // Unix timestamp (null if active)
  project: string;
  task?: string;
  notes?: string;
  git_commits: string[]; // Array of commit hashes
  status: 'active' | 'paused' | 'completed';
  created_at: number;
  updated_at: number;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  directory_patterns: string[]; // Glob patterns for matching directories
  git_repos: string[]; // Git repository paths
  default_task?: string;
  color?: string; // For CLI display
  created_at: number;
}

export interface Task {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  file_patterns?: string[]; // Glob patterns for matching files
  created_at: number;
}

export interface FileActivity {
  id: string;
  timestamp: number;
  file_path: string;
  event_type: 'add' | 'change' | 'unlink';
  project_suggestion?: string;
  task_suggestion?: string;
}

export interface GitCommit {
  hash: string;
  timestamp: number;
  message: string;
  author: string;
  repository: string;
  time_entry_id?: string;
}

export interface AppConfig {
  version: string;
  data_directory: string;
  database_path: string;
  watch_directories: string[];
  ignore_patterns: string[];
  default_project?: string;
  auto_suggest_enabled: boolean;
  file_watcher_enabled: boolean;
  git_integration_enabled: boolean;
  debounce_interval: number; // milliseconds
  suggestions_confidence_threshold: number; // 0-1
}

export interface ProjectMapping {
  pattern: string; // Glob or regex pattern
  project_name: string;
  priority: number; // Higher priority takes precedence
}

export interface ReportOptions {
  start_date?: number;
  end_date?: number;
  project?: string;
  task?: string;
  group_by?: 'project' | 'task' | 'date';
  include_commits?: boolean;
  output_format?: 'table' | 'json' | 'csv' | 'markdown';
}

export interface ReportEntry {
  project: string;
  task?: string;
  duration: number; // seconds
  start_time: number;
  end_time: number;
  notes?: string;
  commit_count: number;
  commits?: GitCommit[];
}

export interface Suggestion {
  project: string;
  task?: string;
  confidence: number; // 0-1
  reason: string;
}

export interface DaemonStatus {
  running: boolean;
  pid?: number;
  uptime?: number;
  activities_logged: number;
}

// Database interface types
export interface Database {
  init(): Promise<void>;
  createTimeEntry(entry: Omit<TimeEntry, 'id' | 'created_at' | 'updated_at'>): Promise<string>;
  updateTimeEntry(id: string, updates: Partial<TimeEntry>): Promise<void>;
  getTimeEntry(id: string): Promise<TimeEntry | null>;
  getActiveTimeEntry(): Promise<TimeEntry | null>;
  listTimeEntries(filters?: Partial<TimeEntry>): Promise<TimeEntry[]>;
  deleteTimeEntry(id: string): Promise<void>;
  createProject(project: Omit<Project, 'id' | 'created_at'>): Promise<string>;
  getProject(id: string): Promise<Project | null>;
  listProjects(): Promise<Project[]>;
  updateProject(id: string, updates: Partial<Project>): Promise<void>;
  deleteProject(id: string): Promise<void>;
  createTask(task: Omit<Task, 'id' | 'created_at'>): Promise<string>;
  listTasks(project_id?: string): Promise<Task[]>;
  logActivity(activity: Omit<FileActivity, 'id'>): Promise<void>;
  getRecentActivities(limit?: number): Promise<FileActivity[]>;
  linkCommitToTimeEntry(commitHash: string, timeEntryId: string): Promise<void>;
  getTimeRangeEntries(start: number, end: number): Promise<TimeEntry[]>;
  close(): void;
}
