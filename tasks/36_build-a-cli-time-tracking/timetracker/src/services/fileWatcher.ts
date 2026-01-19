import chokidar from 'chokidar';
import { Database, FileActivity } from '../types';
import path from 'path';
import fs from 'fs';

export class FileWatcher {
  private watcher: chokidar.FSWatcher | null = null;
  private activityBuffer: Map<string, NodeJS.Timeout> = new Map();
  private debounceMs = 1000;

  constructor(private db: Database) {}

  async start(directories?: string[]): Promise<void> {
    const watchDirs = directories || this.getDefaultDirectories();

    // Filter out non-existent directories
    const validDirs = watchDirs.filter((dir) => {
      const expandedPath = this.expandPath(dir);
      return fs.existsSync(expandedPath);
    });

    if (validDirs.length === 0) {
      throw new Error('No valid directories to watch');
    }

    console.log(`Watching ${validDirs.length} directories:`);
    validDirs.forEach((dir) => console.log(`  - ${this.expandPath(dir)}`));

    // Initialize watcher
    this.watcher = chokidar.watch(validDirs.map((d) => this.expandPath(d)), {
      ignored: this.getIgnorePatterns(),
      persistent: true,
      ignoreInitial: false,
      awaitWriteFinish: {
        stabilityThreshold: 2000,
        pollInterval: 100,
      },
    });

    // Setup event handlers
    this.watcher
      .on('add', (filePath) => this.handleFileEvent(filePath, 'add'))
      .on('change', (filePath) => this.handleFileEvent(filePath, 'change'))
      .on('unlink', (filePath) => this.handleFileEvent(filePath, 'unlink'))
      .on('error', (error) => console.error(`Watcher error: ${error}`))
      .on('ready', () => console.log('File watcher is ready'));
  }

  stop(): void {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
  }

  private async handleFileEvent(filePath: string, eventType: 'add' | 'change' | 'unlink'): Promise<void> {
    // Debounce rapid file changes
    const key = `${filePath}-${eventType}`;

    if (this.activityBuffer.has(key)) {
      clearTimeout(this.activityBuffer.get(key)!);
    }

    const timeout = setTimeout(async () => {
      await this.logActivity(filePath, eventType);
      this.activityBuffer.delete(key);
    }, this.debounceMs);

    this.activityBuffer.set(key, timeout);
  }

  private async logActivity(filePath: string, eventType: 'add' | 'change' | 'unlink'): Promise<void> {
    const suggestions = await this.getSuggestions(filePath);

    const activity: Omit<FileActivity, 'id'> = {
      timestamp: Date.now(),
      file_path: filePath,
      event_type: eventType,
      project_suggestion: suggestions.project,
      task_suggestion: suggestions.task,
    };

    await this.db.logActivity(activity);
  }

  private async getSuggestions(filePath: string): Promise<{ project?: string; task?: string }> {
    // This is a simple implementation
    // The full SuggestionEngine will be implemented separately
    const projects = await this.db.listProjects();

    for (const project of projects) {
      for (const pattern of project.directory_patterns) {
        const expandedPattern = this.expandPath(pattern);
        if (this.matchesPattern(filePath, expandedPattern)) {
          return { project: project.name };
        }
      }
    }

    return {};
  }

  private matchesPattern(filePath: string, pattern: string): boolean {
    // Simple glob pattern matching
    // For production, use a proper glob library like minimatch
    const regex = new RegExp(
      '^' +
        pattern
          .replace(/\*/g, '.*')
          .replace(/\?/g, '.') +
        '$'
    );
    return regex.test(filePath);
  }

  private getDefaultDirectories(): string[] {
    return [
      path.join(require('os').homedir(), 'projects'),
      path.join(require('os').homedir(), 'work'),
      path.join(require('os').homedir(), 'code'),
      process.cwd(),
    ];
  }

  private getIgnorePatterns(): string[] {
    return [
      '**/node_modules/**',
      '**/.git/**',
      '**/dist/**',
      '**/build/**',
      '**/.next/**',
      '**/coverage/**',
      '**/*.tmp',
      '**/*.log',
      '**/.DS_Store',
      '**/.___tmp__',
    ];
  }

  private expandPath(filePath: string): string {
    // Expand ~ to home directory
    if (filePath.startsWith('~')) {
      return filePath.replace('~', require('os').homedir());
    }
    return filePath;
  }
}
