import { Database, Project } from '../types';
import inquirer from 'inquirer';
import chalk from 'chalk';
import Table from 'cli-table3';

export class ProjectCommands {
  constructor(private db: Database) {}

  async create(name: string, description?: string, directoryPatterns?: string[]): Promise<void> {
    const existingProjects = await this.db.listProjects();
    const exists = existingProjects.some((p) => p.name === name);

    if (exists) {
      console.log(chalk.red(`✗ Project "${name}" already exists.`));
      return;
    }

    let patterns = directoryPatterns;
    if (!patterns) {
      const { patternsInput } = await inquirer.prompt([
        {
          type: 'input',
          name: 'patternsInput',
          message: 'Enter directory patterns (comma-separated, optional):',
          default: '',
        },
      ]);
      patterns = patternsInput ? patternsInput.split(',').map((p: string) => p.trim()) : [];
    }

    await this.db.createProject({
      name,
      description,
      directory_patterns: patterns || [],
      git_repos: [],
    });

    console.log(chalk.green(`✓ Project "${name}" created successfully.`));
  }

  async list(): Promise<void> {
    const projects = await this.db.listProjects();

    if (projects.length === 0) {
      console.log(chalk.gray('No projects found.'));
      return;
    }

    const table = new Table({
      head: [chalk.cyan('Name'), chalk.cyan('Description'), chalk.cyan('Patterns'), chalk.cyan('Repos')],
      colWidths: [30, 40, 30, 20],
    });

    projects.forEach((project) => {
      table.push([
        project.name,
        project.description || '-',
        project.directory_patterns.length > 0
          ? project.directory_patterns.join(', ')
          : '-',
        project.git_repos.length > 0 ? project.git_repos.length.toString() : '0',
      ]);
    });

    console.log(table.toString());
  }

  async delete(name: string): Promise<void> {
    const projects = await this.db.listProjects();
    const project = projects.find((p) => p.name === name);

    if (!project) {
      console.log(chalk.red(`✗ Project "${name}" not found.`));
      return;
    }

    const { confirm } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirm',
        message: `Are you sure you want to delete project "${name}"?`,
        default: false,
      },
    ]);

    if (!confirm) {
      console.log(chalk.yellow('Cancelled.'));
      return;
    }

    await this.db.deleteProject(project.id);
    console.log(chalk.green(`✓ Project "${name}" deleted successfully.`));
  }

  async update(name: string): Promise<void> {
    const projects = await this.db.listProjects();
    const project = projects.find((p) => p.name === name);

    if (!project) {
      console.log(chalk.red(`✗ Project "${name}" not found.`));
      return;
    }

    const answers = await inquirer.prompt([
      {
        type: 'list',
        name: 'updateField',
        message: 'What do you want to update?',
        choices: [
          { name: 'Name', value: 'name' },
          { name: 'Description', value: 'description' },
          { name: 'Directory patterns', value: 'patterns' },
        ],
      },
      {
        type: 'input',
        name: 'newValue',
        message: (answers: any) => `Enter new ${answers.updateField}:`,
        default: (answers: any) =>
          answers.updateField === 'description'
            ? project.description || ''
            : answers.updateField === 'patterns'
            ? project.directory_patterns.join(', ')
            : '',
      },
    ]);

    const updateField = answers.updateField;
    const newValue = answers.newValue;

    const updates: Partial<Project> = {};

    if (updateField === 'name') {
      updates.name = newValue;
    } else if (updateField === 'description') {
      updates.description = newValue || undefined;
    } else if (updateField === 'patterns') {
      updates.directory_patterns = newValue ? newValue.split(',').map((p: string) => p.trim()) : [];
    }

    await this.db.updateProject(project.id, updates);
    console.log(chalk.green(`✓ Project "${name}" updated successfully.`));
  }
}
