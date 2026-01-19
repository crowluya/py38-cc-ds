import { Database, TimeEntry, Suggestion } from '../types';
import inquirer from 'inquirer';
import chalk from 'chalk';
import dayjs from 'dayjs';

export class TimeTrackerCommands {
  constructor(private db: Database) {}

  async start(project?: string, task?: string, notes?: string): Promise<void> {
    // Check if there's already an active entry
    const activeEntry = await this.db.getActiveTimeEntry();
    if (activeEntry) {
      console.log(chalk.yellow('⚠ You already have an active time entry:'));
      console.log(chalk.cyan(`  Project: ${activeEntry.project}`));
      if (activeEntry.task) {
        console.log(chalk.cyan(`  Task: ${activeEntry.task}`));
      }
      console.log(chalk.cyan(`  Started: ${dayjs(activeEntry.start_time).format('YYYY-MM-DD HH:mm:ss')}`));
      console.log(chalk.yellow('\nUse "track stop" to end it before starting a new one.'));
      return;
    }

    let selectedProject = project;
    let selectedTask = task;
    let selectedNotes = notes;

    // If no project specified, prompt for it
    if (!selectedProject) {
      const projects = await this.db.listProjects();
      if (projects.length === 0) {
        console.log(chalk.red('No projects found. Create one first with "track project create"'));
        return;
      }

      const { projectChoice } = await inquirer.prompt([
        {
          type: 'list',
          name: 'projectChoice',
          message: 'Select a project:',
          choices: projects.map((p) => ({
            name: p.name + (p.description ? ` - ${p.description}` : ''),
            value: p.name,
          })),
        },
      ]);
      selectedProject = projectChoice;
    }

    // If no task specified, prompt for it (optional)
    if (!selectedTask) {
      const projects = await this.db.listProjects();
      const tasks = await this.db.listTasks();
      const projectTasks = tasks.filter((t) => {
        const project = projects.find((p) => p.name === selectedProject);
        return project && t.project_id === project.id;
      });

      if (projectTasks.length > 0) {
        const { taskChoice, shouldAddTask } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'shouldAddTask',
            message: 'Do you want to add a task?',
            default: false,
          },
          {
            type: 'list',
            name: 'taskChoice',
            message: 'Select a task:',
            choices: [
              { name: 'Skip task', value: null },
              ...projectTasks.map((t) => ({
                name: t.name + (t.description ? ` - ${t.description}` : ''),
                value: t.name,
              })),
            ],
            when: (answers) => answers.shouldAddTask,
          },
        ]);
        selectedTask = taskChoice;
      }
    }

    // Prompt for notes (optional)
    if (!selectedNotes) {
      const { notesInput } = await inquirer.prompt([
        {
          type: 'input',
          name: 'notesInput',
          message: 'Add notes (optional):',
          default: '',
        },
      ]);
      selectedNotes = notesInput || undefined;
    }

    // Create the time entry
    const entryId = await this.db.createTimeEntry({
      start_time: Date.now(),
      project: selectedProject!,
      task: selectedTask,
      notes: selectedNotes,
      git_commits: [],
      status: 'active',
    });

    console.log(chalk.green('✓ Time tracking started'));
    console.log(chalk.cyan(`  ID: ${entryId}`));
    console.log(chalk.cyan(`  Project: ${selectedProject}`));
    if (selectedTask) {
      console.log(chalk.cyan(`  Task: ${selectedTask}`));
    }
    if (selectedNotes) {
      console.log(chalk.cyan(`  Notes: ${selectedNotes}`));
    }
    console.log(chalk.cyan(`  Started: ${dayjs().format('YYYY-MM-DD HH:mm:ss')}`));
  }

  async stop(): Promise<void> {
    const activeEntry = await this.db.getActiveTimeEntry();
    if (!activeEntry) {
      console.log(chalk.yellow('⚠ No active time entry found. Use "track start" to begin tracking.'));
      return;
    }

    const endTime = Date.now();
    const duration = endTime - activeEntry.start_time;
    const formattedDuration = this.formatDuration(duration);

    // Prompt for final notes
    const { finalNotes } = await inquirer.prompt([
      {
        type: 'input',
        name: 'finalNotes',
        message: 'Add final notes (optional):',
        default: activeEntry.notes || '',
      },
    ]);

    await this.db.updateTimeEntry(activeEntry.id, {
      end_time: endTime,
      status: 'completed',
      notes: finalNotes || undefined,
    });

    console.log(chalk.green('✓ Time tracking stopped'));
    console.log(chalk.cyan(`  Project: ${activeEntry.project}`));
    if (activeEntry.task) {
      console.log(chalk.cyan(`  Task: ${activeEntry.task}`));
    }
    console.log(chalk.cyan(`  Duration: ${formattedDuration}`));
    console.log(chalk.cyan(`  Ended: ${dayjs(endTime).format('YYYY-MM-DD HH:mm:ss')}`));
  }

  async pause(): Promise<void> {
    const activeEntry = await this.db.getActiveTimeEntry();
    if (!activeEntry) {
      console.log(chalk.yellow('⚠ No active time entry found.'));
      return;
    }

    if (activeEntry.status === 'paused') {
      console.log(chalk.yellow('⚠ Time entry is already paused.'));
      return;
    }

    await this.db.updateTimeEntry(activeEntry.id, { status: 'paused' });
    console.log(chalk.green('✓ Time tracking paused'));
    console.log(chalk.cyan(`  Project: ${activeEntry.project}`));
  }

  async resume(): Promise<void> {
    const pausedEntry = await this.db.getActiveTimeEntry();
    if (!pausedEntry) {
      console.log(chalk.yellow('⚠ No paused time entry found.'));
      return;
    }

    if (pausedEntry.status !== 'paused') {
      console.log(chalk.yellow('⚠ Current entry is not paused.'));
      return;
    }

    await this.db.updateTimeEntry(pausedEntry.id, { status: 'active' });
    console.log(chalk.green('✓ Time tracking resumed'));
    console.log(chalk.cyan(`  Project: ${pausedEntry.project}`));
  }

  async status(): Promise<void> {
    const activeEntry = await this.db.getActiveTimeEntry();
    if (!activeEntry) {
      console.log(chalk.gray('No active time entry.'));
      return;
    }

    const currentTime = Date.now();
    const elapsed = activeEntry.status === 'paused'
      ? activeEntry.end_time! - activeEntry.start_time
      : currentTime - activeEntry.start_time;
    const formattedElapsed = this.formatDuration(elapsed);

    console.log(chalk.bold('Current Time Entry:'));
    console.log(chalk.cyan(`  Status: ${activeEntry.status.toUpperCase()}`));
    console.log(chalk.cyan(`  Project: ${activeEntry.project}`));
    if (activeEntry.task) {
      console.log(chalk.cyan(`  Task: ${activeEntry.task}`));
    }
    if (activeEntry.notes) {
      console.log(chalk.cyan(`  Notes: ${activeEntry.notes}`));
    }
    console.log(chalk.cyan(`  Started: ${dayjs(activeEntry.start_time).format('YYYY-MM-DD HH:mm:ss')}`));
    console.log(chalk.cyan(`  Elapsed: ${formattedElapsed}`));
    if (activeEntry.git_commits.length > 0) {
      console.log(chalk.cyan(`  Git Commits: ${activeEntry.git_commits.length}`));
    }
  }

  async list(limit: number = 10): Promise<void> {
    const entries = await this.db.listTimeEntries();
    const recentEntries = entries.slice(0, limit);

    if (recentEntries.length === 0) {
      console.log(chalk.gray('No time entries found.'));
      return;
    }

    console.log(chalk.bold(`Recent Time Entries (last ${limit}):\n`));

    recentEntries.forEach((entry) => {
      const duration = entry.end_time
        ? this.formatDuration(entry.end_time - entry.start_time)
        : this.formatDuration(Date.now() - entry.start_time) + ' (ongoing)';

      const statusColor =
        entry.status === 'active' ? chalk.green :
        entry.status === 'paused' ? chalk.yellow :
        chalk.gray;

      console.log(statusColor(`[${entry.status.toUpperCase()}]`) + chalk.cyan(` ${entry.project}`));
      if (entry.task) {
        console.log(chalk.gray(`  Task: ${entry.task}`));
      }
      console.log(chalk.gray(`  Duration: ${duration}`));
      console.log(chalk.gray(`  Started: ${dayjs(entry.start_time).format('YYYY-MM-DD HH:mm:ss')}`));
      if (entry.notes) {
        console.log(chalk.gray(`  Notes: ${entry.notes}`));
      }
      console.log('');
    });
  }

  async suggest(suggestions: Suggestion[]): Promise<void> {
    if (suggestions.length === 0) {
      console.log(chalk.gray('No suggestions available.'));
      return;
    }

    console.log(chalk.bold('\n💡 Suggestions based on your recent activity:\n'));

    suggestions.slice(0, 5).forEach((suggestion, index) => {
      const confidencePercent = Math.round(suggestion.confidence * 100);
      const confidenceColor =
        suggestion.confidence >= 0.8 ? chalk.green :
        suggestion.confidence >= 0.5 ? chalk.yellow :
        chalk.gray;

      console.log(`${index + 1}. ${chalk.cyan(suggestion.project)}`);
      if (suggestion.task) {
        console.log(chalk.gray(`   Task: ${suggestion.task}`));
      }
      console.log(confidenceColor(`   Confidence: ${confidencePercent}%`));
      console.log(chalk.gray(`   Reason: ${suggestion.reason}`));
      console.log('');
    });
  }

  private formatDuration(milliseconds: number): string {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    } else if (minutes > 0) {
      const secs = seconds % 60;
      return `${minutes}m ${secs}s`;
    } else {
      return `${seconds}s`;
    }
  }
}
