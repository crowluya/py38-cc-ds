import sqlite3 from 'sqlite3';
import { Database, TimeEntry, Project, Task, FileActivity, GitCommit } from '../types';
import path from 'path';
import os from 'os';

export class SQLiteDatabase implements Database {
  private db: sqlite3.Database | null = null;
  private dbPath: string;

  constructor(dbPath?: string) {
    this.dbPath = dbPath || path.join(os.homedir(), '.timetracker', 'timetracker.db');
  }

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(this.dbPath, (err) => {
        if (err) {
          reject(err);
        } else {
          this.createTables()
            .then(() => resolve())
            .catch(reject);
        }
      });
    });
  }

  private async createTables(): Promise<void> {
    const tables = [
      `CREATE TABLE IF NOT EXISTS time_entries (
        id TEXT PRIMARY KEY,
        start_time INTEGER NOT NULL,
        end_time INTEGER,
        project TEXT NOT NULL,
        task TEXT,
        notes TEXT,
        git_commits TEXT,
        status TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      )`,
      `CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        directory_patterns TEXT,
        git_repos TEXT,
        default_task TEXT,
        color TEXT,
        created_at INTEGER NOT NULL
      )`,
      `CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        file_patterns TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
      )`,
      `CREATE TABLE IF NOT EXISTS file_activities (
        id TEXT PRIMARY KEY,
        timestamp INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        event_type TEXT NOT NULL,
        project_suggestion TEXT,
        task_suggestion TEXT
      )`,
      `CREATE TABLE IF NOT EXISTS git_commits (
        hash TEXT PRIMARY KEY,
        timestamp INTEGER NOT NULL,
        message TEXT NOT NULL,
        author TEXT NOT NULL,
        repository TEXT NOT NULL,
        time_entry_id TEXT,
        FOREIGN KEY (time_entry_id) REFERENCES time_entries(id)
      )`,
      `CREATE INDEX IF NOT EXISTS idx_time_entries_status ON time_entries(status)`,
      `CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project)`,
      `CREATE INDEX IF NOT EXISTS idx_file_activities_timestamp ON file_activities(timestamp)`,
    ];

    for (const tableSQL of tables) {
      await this.run(tableSQL);
    }
  }

  private run(sql: string, params: any[] = []): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db!.run(sql, params, function (err) {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  private get(sql: string, params: any[] = []): Promise<any> {
    return new Promise((resolve, reject) => {
      this.db!.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  private all(sql: string, params: any[] = []): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db!.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  async createTimeEntry(entry: Omit<TimeEntry, 'id' | 'created_at' | 'updated_at'>): Promise<string> {
    const id = this.generateId();
    const now = Date.now();
    const sql = `
      INSERT INTO time_entries (id, start_time, end_time, project, task, notes, git_commits, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    await this.run(sql, [
      id,
      entry.start_time,
      entry.end_time || null,
      entry.project,
      entry.task || null,
      entry.notes || null,
      JSON.stringify(entry.git_commits || []),
      entry.status,
      now,
      now,
    ]);
    return id;
  }

  async updateTimeEntry(id: string, updates: Partial<TimeEntry>): Promise<void> {
    const fields: string[] = [];
    const values: any[] = [];

    if (updates.end_time !== undefined) {
      fields.push('end_time = ?');
      values.push(updates.end_time);
    }
    if (updates.project !== undefined) {
      fields.push('project = ?');
      values.push(updates.project);
    }
    if (updates.task !== undefined) {
      fields.push('task = ?');
      values.push(updates.task);
    }
    if (updates.notes !== undefined) {
      fields.push('notes = ?');
      values.push(updates.notes);
    }
    if (updates.git_commits !== undefined) {
      fields.push('git_commits = ?');
      values.push(JSON.stringify(updates.git_commits));
    }
    if (updates.status !== undefined) {
      fields.push('status = ?');
      values.push(updates.status);
    }

    fields.push('updated_at = ?');
    values.push(Date.now());
    values.push(id);

    const sql = `UPDATE time_entries SET ${fields.join(', ')} WHERE id = ?`;
    await this.run(sql, values);
  }

  async getTimeEntry(id: string): Promise<TimeEntry | null> {
    const row = await this.get('SELECT * FROM time_entries WHERE id = ?', [id]);
    return row ? this.mapTimeEntry(row) : null;
  }

  async getActiveTimeEntry(): Promise<TimeEntry | null> {
    const row = await this.get('SELECT * FROM time_entries WHERE status = ? ORDER BY start_time DESC LIMIT 1', ['active']);
    return row ? this.mapTimeEntry(row) : null;
  }

  async listTimeEntries(filters?: Partial<TimeEntry>): Promise<TimeEntry[]> {
    let sql = 'SELECT * FROM time_entries WHERE 1=1';
    const params: any[] = [];

    if (filters?.project) {
      sql += ' AND project = ?';
      params.push(filters.project);
    }
    if (filters?.status) {
      sql += ' AND status = ?';
      params.push(filters.status);
    }
    if (filters?.task) {
      sql += ' AND task = ?';
      params.push(filters.task);
    }

    sql += ' ORDER BY start_time DESC';

    const rows = await this.all(sql, params);
    return rows.map(this.mapTimeEntry);
  }

  async deleteTimeEntry(id: string): Promise<void> {
    await this.run('DELETE FROM time_entries WHERE id = ?', [id]);
  }

  async createProject(project: Omit<Project, 'id' | 'created_at'>): Promise<string> {
    const id = this.generateId();
    const now = Date.now();
    const sql = `
      INSERT INTO projects (id, name, description, directory_patterns, git_repos, default_task, color, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `;
    await this.run(sql, [
      id,
      project.name,
      project.description || null,
      JSON.stringify(project.directory_patterns || []),
      JSON.stringify(project.git_repos || []),
      project.default_task || null,
      project.color || null,
      now,
    ]);
    return id;
  }

  async getProject(id: string): Promise<Project | null> {
    const row = await this.get('SELECT * FROM projects WHERE id = ?', [id]);
    return row ? this.mapProject(row) : null;
  }

  async listProjects(): Promise<Project[]> {
    const rows = await this.all('SELECT * FROM projects ORDER BY name');
    return rows.map(this.mapProject);
  }

  async updateProject(id: string, updates: Partial<Project>): Promise<void> {
    const fields: string[] = [];
    const values: any[] = [];

    if (updates.name !== undefined) {
      fields.push('name = ?');
      values.push(updates.name);
    }
    if (updates.description !== undefined) {
      fields.push('description = ?');
      values.push(updates.description);
    }
    if (updates.directory_patterns !== undefined) {
      fields.push('directory_patterns = ?');
      values.push(JSON.stringify(updates.directory_patterns));
    }
    if (updates.git_repos !== undefined) {
      fields.push('git_repos = ?');
      values.push(JSON.stringify(updates.git_repos));
    }
    if (updates.default_task !== undefined) {
      fields.push('default_task = ?');
      values.push(updates.default_task);
    }
    if (updates.color !== undefined) {
      fields.push('color = ?');
      values.push(updates.color);
    }

    values.push(id);
    const sql = `UPDATE projects SET ${fields.join(', ')} WHERE id = ?`;
    await this.run(sql, values);
  }

  async deleteProject(id: string): Promise<void> {
    await this.run('DELETE FROM projects WHERE id = ?', [id]);
  }

  async createTask(task: Omit<Task, 'id' | 'created_at'>): Promise<string> {
    const id = this.generateId();
    const now = Date.now();
    const sql = `
      INSERT INTO tasks (id, project_id, name, description, file_patterns, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `;
    await this.run(sql, [
      id,
      task.project_id,
      task.name,
      task.description || null,
      JSON.stringify(task.file_patterns || []),
      now,
    ]);
    return id;
  }

  async listTasks(project_id?: string): Promise<Task[]> {
    let sql = 'SELECT * FROM tasks';
    const params: any[] = [];

    if (project_id) {
      sql += ' WHERE project_id = ?';
      params.push(project_id);
    }

    const rows = await this.all(sql, params);
    return rows.map(this.mapTask);
  }

  async logActivity(activity: Omit<FileActivity, 'id'>): Promise<void> {
    const id = this.generateId();
    const sql = `
      INSERT INTO file_activities (id, timestamp, file_path, event_type, project_suggestion, task_suggestion)
      VALUES (?, ?, ?, ?, ?, ?)
    `;
    await this.run(sql, [
      id,
      activity.timestamp,
      activity.file_path,
      activity.event_type,
      activity.project_suggestion || null,
      activity.task_suggestion || null,
    ]);
  }

  async getRecentActivities(limit: number = 100): Promise<FileActivity[]> {
    const sql = 'SELECT * FROM file_activities ORDER BY timestamp DESC LIMIT ?';
    const rows = await this.all(sql, [limit]);
    return rows.map(this.mapFileActivity);
  }

  async linkCommitToTimeEntry(commitHash: string, timeEntryId: string): Promise<void> {
    await this.run('UPDATE git_commits SET time_entry_id = ? WHERE hash = ?', [timeEntryId, commitHash]);
  }

  async getTimeRangeEntries(start: number, end: number): Promise<TimeEntry[]> {
    const sql = `
      SELECT * FROM time_entries
      WHERE start_time >= ? AND start_time <= ?
      OR end_time >= ? AND end_time <= ?
      OR start_time <= ? AND end_time >= ?
      ORDER BY start_time
    `;
    const rows = await this.all(sql, [start, end, start, end, start, end]);
    return rows.map(this.mapTimeEntry);
  }

  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private mapTimeEntry(row: any): TimeEntry {
    return {
      id: row.id,
      start_time: row.start_time,
      end_time: row.end_time,
      project: row.project,
      task: row.task,
      notes: row.notes,
      git_commits: JSON.parse(row.git_commits || '[]'),
      status: row.status,
      created_at: row.created_at,
      updated_at: row.updated_at,
    };
  }

  private mapProject(row: any): Project {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      directory_patterns: JSON.parse(row.directory_patterns || '[]'),
      git_repos: JSON.parse(row.git_repos || '[]'),
      default_task: row.default_task,
      color: row.color,
      created_at: row.created_at,
    };
  }

  private mapTask(row: any): Task {
    return {
      id: row.id,
      project_id: row.project_id,
      name: row.name,
      description: row.description,
      file_patterns: row.file_patterns ? JSON.parse(row.file_patterns) : undefined,
      created_at: row.created_at,
    };
  }

  private mapFileActivity(row: any): FileActivity {
    return {
      id: row.id,
      timestamp: row.timestamp,
      file_path: row.file_path,
      event_type: row.event_type,
      project_suggestion: row.project_suggestion,
      task_suggestion: row.task_suggestion,
    };
  }
}
