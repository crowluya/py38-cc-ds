import { Database, ProjectMapping, Project } from '../types';
import path from 'path';
import fs from 'fs';
import os from 'os';

export interface MatchResult {
  project: string;
  task?: string;
  confidence: number;
  matchedPattern: string;
}

export class ProjectMatcher {
  private mappings: ProjectMapping[] = [];
  private cache: Map<string, MatchResult> = new Map();
  private cacheMaxSize = 1000;
  private cacheTTL = 5 * 60 * 1000; // 5 minutes
  private cacheTimestamps: Map<string, number> = new Map();

  constructor(private db: Database) {
    this.loadMappings();
  }

  async loadMappings(): Promise<void> {
    const configPath = path.join(os.homedir(), '.timetracker', 'project-mappings.json');

    if (fs.existsSync(configPath)) {
      try {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        this.mappings = config.mappings || [];
      } catch (error) {
        console.error('Error loading project mappings:', error);
        this.mappings = [];
      }
    }
  }

  async match(filePath: string): Promise<MatchResult | null> {
    // Check cache first
    const cachedResult = this.getFromCache(filePath);
    if (cachedResult) {
      return cachedResult;
    }

    // Sort mappings by priority (higher first)
    const sortedMappings = [...this.mappings].sort((a, b) => b.priority - a.priority);

    for (const mapping of sortedMappings) {
      const expandedPattern = this.expandPath(mapping.pattern);

      if (this.matches(filePath, expandedPattern)) {
        const result: MatchResult = {
          project: mapping.project_name,
          confidence: this.calculateConfidence(mapping.priority),
          matchedPattern: mapping.pattern,
        };

        this.addToCache(filePath, result);
        return result;
      }
    }

    // Try matching against database projects
    const projects = await this.db.listProjects();
    for (const project of projects) {
      for (const pattern of project.directory_patterns) {
        const expandedPattern = this.expandPath(pattern);

        if (this.matches(filePath, expandedPattern)) {
          const result: MatchResult = {
            project: project.name,
            confidence: 0.6,
            matchedPattern: pattern,
          };

          this.addToCache(filePath, result);
          return result;
        }
      }
    }

    return null;
  }

  async matchTask(filePath: string, projectId: string): Promise<string | null> {
    const tasks = await this.db.listTasks(projectId);

    for (const task of tasks) {
      if (!task.file_patterns) continue;

      for (const pattern of task.file_patterns) {
        const expandedPattern = this.expandPath(pattern);

        if (this.matches(filePath, expandedPattern)) {
          return task.name;
        }
      }
    }

    return null;
  }

  async matchFromDirectory(dirPath: string): Promise<MatchResult | null> {
    const projects = await this.db.listProjects();

    for (const project of projects) {
      for (const pattern of project.directory_patterns) {
        const expandedPattern = this.expandPath(pattern);

        if (this.matches(dirPath, expandedPattern) || dirPath.includes(expandedPattern)) {
          return {
            project: project.name,
            confidence: 0.8,
            matchedPattern: pattern,
          };
        }
      }
    }

    return null;
  }

  private matches(filePath: string, pattern: string): boolean {
    try {
      // Convert glob pattern to regex
      const regexPattern = pattern
        .replace(/\*\*/g, '.*')
        .replace(/\*/g, '[^/]*')
        .replace(/\?/g, '[^/]');
      const regex = new RegExp(regexPattern);
      return regex.test(filePath);
    } catch {
      // Fallback to simple string matching if pattern is invalid
      return filePath.includes(pattern.replace(/\*/g, ''));
    }
  }

  private calculateConfidence(priority: number): number {
    // Map priority (0-100) to confidence (0-1)
    const normalized = Math.min(Math.max(priority, 0), 100);
    return 0.5 + (normalized / 100) * 0.5; // Range from 0.5 to 1.0
  }

  private addToCache(filePath: string, result: MatchResult): void {
    // Implement simple LRU cache
    if (this.cache.size >= this.cacheMaxSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) {
        this.cache.delete(oldestKey);
        this.cacheTimestamps.delete(oldestKey);
      }
    }

    this.cache.set(filePath, result);
    this.cacheTimestamps.set(filePath, Date.now());
  }

  private getFromCache(filePath: string): MatchResult | null {
    const result = this.cache.get(filePath);
    const timestamp = this.cacheTimestamps.get(filePath);

    if (!result || !timestamp) return null;

    // Check if cache entry is still valid
    if (Date.now() - timestamp > this.cacheTTL) {
      this.cache.delete(filePath);
      this.cacheTimestamps.delete(filePath);
      return null;
    }

    return result;
  }

  private expandPath(filePath: string): string {
    if (filePath.startsWith('~')) {
      return filePath.replace('~', os.homedir());
    }
    return filePath;
  }

  clearCache(): void {
    this.cache.clear();
    this.cacheTimestamps.clear();
  }
}
