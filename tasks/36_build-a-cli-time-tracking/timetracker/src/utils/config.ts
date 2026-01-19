import fs from 'fs';
import path from 'path';
import os from 'os';
import { AppConfig } from '../types';

const DEFAULT_CONFIG: AppConfig = {
  version: '1.0.0',
  data_directory: path.join(os.homedir(), '.timetracker'),
  database_path: path.join(os.homedir(), '.timetracker', 'timetracker.db'),
  watch_directories: [
    path.join(os.homedir(), 'projects'),
    path.join(os.homedir(), 'work'),
    path.join(os.homedir(), 'code'),
  ],
  ignore_patterns: [
    '**/node_modules/**',
    '**/.git/**',
    '**/dist/**',
    '**/build/**',
    '**/.next/**',
    '**/coverage/**',
    '**/*.tmp',
    '**/*.log',
    '**/.DS_Store',
  ],
  auto_suggest_enabled: true,
  file_watcher_enabled: true,
  git_integration_enabled: true,
  debounce_interval: 1000,
  suggestions_confidence_threshold: 0.5,
};

export class ConfigManager {
  private config: AppConfig;
  private configPath: string;

  constructor(configPath?: string) {
    this.configPath = configPath || path.join(os.homedir(), '.timetracker', 'config.json');
    this.config = this.loadConfig();
  }

  loadConfig(): AppConfig {
    if (fs.existsSync(this.configPath)) {
      try {
        const data = fs.readFileSync(this.configPath, 'utf-8');
        const loaded = JSON.parse(data);
        return { ...DEFAULT_CONFIG, ...loaded };
      } catch (error) {
        console.error('Error loading config, using defaults:', error);
        return { ...DEFAULT_CONFIG };
      }
    }

    // Create default config
    this.saveConfig(DEFAULT_CONFIG);
    return { ...DEFAULT_CONFIG };
  }

  saveConfig(config: AppConfig): void {
    const configDir = path.dirname(this.configPath);

    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }

    fs.writeFileSync(this.configPath, JSON.stringify(config, null, 2));
    this.config = config;
  }

  get<K extends keyof AppConfig>(key: K): AppConfig[K] {
    return this.config[key];
  }

  set<K extends keyof AppConfig>(key: K, value: AppConfig[K]): void {
    this.config[key] = value;
    this.saveConfig(this.config);
  }

  getAll(): AppConfig {
    return { ...this.config };
  }

  update(updates: Partial<AppConfig>): void {
    this.config = { ...this.config, ...updates };
    this.saveConfig(this.config);
  }

  ensureDataDirectory(): void {
    const dataDir = this.config.data_directory;

    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
  }

  addWatchDirectory(directory: string): void {
    const expandedPath = this.expandPath(directory);

    if (!this.config.watch_directories.includes(expandedPath)) {
      this.config.watch_directories.push(expandedPath);
      this.saveConfig(this.config);
    }
  }

  removeWatchDirectory(directory: string): void {
    const expandedPath = this.expandPath(directory);
    this.config.watch_directories = this.config.watch_directories.filter(
      (dir) => dir !== expandedPath
    );
    this.saveConfig(this.config);
  }

  addIgnorePattern(pattern: string): void {
    if (!this.config.ignore_patterns.includes(pattern)) {
      this.config.ignore_patterns.push(pattern);
      this.saveConfig(this.config);
    }
  }

  removeIgnorePattern(pattern: string): void {
    this.config.ignore_patterns = this.config.ignore_patterns.filter((p) => p !== pattern);
    this.saveConfig(this.config);
  }

  private expandPath(filePath: string): string {
    if (filePath.startsWith('~')) {
      return filePath.replace('~', os.homedir());
    }
    return filePath;
  }

  reset(): void {
    this.config = { ...DEFAULT_CONFIG };
    this.saveConfig(this.config);
  }
}
