#!/usr/bin/env node

import { Command } from 'commander';
import path from 'path';
import os from 'os';
import { SQLiteDatabase } from './services/database';
import { TimeTrackerCommands } from './commands';
import { ProjectCommands } from './commands/project';
import { ReportGenerator } from './services/reportGenerator';
import { FileWatcher } from './services/fileWatcher';
import { GitIntegration } from './services/gitIntegration';
import { ConfigManager } from './utils/config';
import chalk from 'chalk';
import { handleError, safeExecute, handleWarning } from './utils/errors';

const program = new Command();
const dataDir = path.join(os.homedir(), '.timetracker');
const dbPath = path.join(dataDir, 'timetracker.db');
const db = new SQLiteDatabase(dbPath);
const config = new ConfigManager();

// Ensure data directory exists
config.ensureDataDirectory();

// Initialize database
async function initDatabase() {
  try {
    await db.init();
  } catch (error) {
    handleError(error);
  }
}

// Wrapper for error handling
function withErrorHandling(handler: () => Promise<void>) {
  return async () => {
    try {
      await handler();
    } catch (error) {
      handleError(error);
    }
  };
}

// CLI configuration
program
  .name('track')
  .description('CLI time-tracking tool with automatic activity detection and git integration')
  .version('1.0.0');

// Start command
program
  .command('start')
  .description('Start tracking time for a project')
  .option('-p, --project <name>', 'Project name')
  .option('-t, --task <name>', 'Task name')
  .option('-n, --notes <notes>', 'Notes')
  .action(async (options) => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.start(options.project, options.task, options.notes);
  });

// Stop command
program
  .command('stop')
  .description('Stop tracking time')
  .action(async () => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.stop();
  });

// Pause command
program
  .command('pause')
  .description('Pause the current time entry')
  .action(async () => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.pause();
  });

// Resume command
program
  .command('resume')
  .description('Resume a paused time entry')
  .action(async () => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.resume();
  });

// Status command
program
  .command('status')
  .description('Show the current time entry status')
  .action(async () => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.status();
  });

// List command
program
  .command('list')
  .description('List recent time entries')
  .option('-l, --limit <number>', 'Number of entries to show', '10')
  .action(async (options) => {
    await initDatabase();
    const commands = new TimeTrackerCommands(db);
    await commands.list(parseInt(options.limit));
  });

// Report command
program
  .command('report')
  .description('Generate time reports')
  .option('-p, --project <name>', 'Filter by project')
  .option('-t, --task <name>', 'Filter by task')
  .option('-d, --days <number>', 'Number of days to include', '7')
  .option('-f, --format <format>', 'Output format (table, json, csv, markdown)', 'table')
  .option('--commits', 'Include git commits in report')
  .action(async (options) => {
    await initDatabase();
    const generator = new ReportGenerator(db);
    const days = parseInt(options.days);
    const startDate = Date.now() - days * 24 * 60 * 60 * 1000;

    await generator.generate({
      start_date: startDate,
      end_date: Date.now(),
      project: options.project,
      task: options.task,
      output_format: options.format,
      include_commits: options.commits,
    });
  });

// Project commands
const projectCmd = program.command('project').description('Manage projects');

projectCmd
  .command('create <name>')
  .description('Create a new project')
  .option('-d, --description <text>', 'Project description')
  .option('-p, --patterns <patterns>', 'Directory patterns (comma-separated)')
  .action(async (name, options) => {
    await initDatabase();
    const commands = new ProjectCommands(db);
    const patterns = options.patterns ? options.patterns.split(',') : undefined;
    await commands.create(name, options.description, patterns);
  });

projectCmd
  .command('list')
  .description('List all projects')
  .action(async () => {
    await initDatabase();
    const commands = new ProjectCommands(db);
    await commands.list();
  });

projectCmd
  .command('delete <name>')
  .description('Delete a project')
  .action(async (name) => {
    await initDatabase();
    const commands = new ProjectCommands(db);
    await commands.delete(name);
  });

projectCmd
  .command('update <name>')
  .description('Update a project')
  .action(async (name) => {
    await initDatabase();
    const commands = new ProjectCommands(db);
    await commands.update(name);
  });

// Watch command
program
  .command('watch')
  .description('Start the file watcher daemon')
  .option('-d, --directories <dirs>', 'Directories to watch (comma-separated)')
  .action(async (options) => {
    await initDatabase();
    const watcher = new FileWatcher(db);
    const directories = options.directories
      ? options.directories.split(',').map((d: string) => d.trim())
      : undefined;

    console.log(chalk.cyan('🔍 Starting file watcher...'));
    await watcher.start(directories);
  });

// Suggestions command
program
  .command('suggest')
  .description('Get project/task suggestions based on recent activity')
  .action(async () => {
    await initDatabase();
    const activities = await db.getRecentActivities(50);

    // Simple suggestion logic (will be enhanced by SuggestionEngine)
    const suggestions = activities.slice(0, 5).map((activity) => ({
      project: activity.project_suggestion || 'Unknown',
      task: activity.task_suggestion,
      confidence: 0.7,
      reason: `Based on recent file activity: ${activity.file_path}`,
    }));

    const commands = new TimeTrackerCommands(db);
    await commands.suggest(suggestions);
  });

// Git sync command
program
  .command('git-sync')
  .description('Sync git commits with time entries')
  .action(async () => {
    await initDatabase();
    const git = new GitIntegration(db);
    console.log(chalk.cyan('🔄 Syncing git commits...'));
    await git.syncCommits();
    console.log(chalk.green('✓ Git sync complete'));
  });

// Parse arguments
program.parse(process.argv);

// Show help if no command provided
if (!process.argv.slice(2).length) {
  program.outputHelp();
}

// Close database on exit
process.on('SIGINT', () => {
  db.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  db.close();
  process.exit(0);
});
