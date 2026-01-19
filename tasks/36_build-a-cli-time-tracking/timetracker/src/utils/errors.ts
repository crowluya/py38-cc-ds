import chalk from 'chalk';

export class TimeTrackerError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'TimeTrackerError';
  }
}

export class DatabaseError extends TimeTrackerError {
  constructor(message: string) {
    super(message, 'DATABASE_ERROR');
    this.name = 'DatabaseError';
  }
}

export class ConfigError extends TimeTrackerError {
  constructor(message: string) {
    super(message, 'CONFIG_ERROR');
    this.name = 'ConfigError';
  }
}

export class ValidationError extends TimeTrackerError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

export class FileNotFoundError extends TimeTrackerError {
  constructor(path: string) {
    super(`File not found: ${path}`, 'FILE_NOT_FOUND');
    this.name = 'FileNotFoundError';
  }
}

export class GitError extends TimeTrackerError {
  constructor(message: string) {
    super(message, 'GIT_ERROR');
    this.name = 'GitError';
  }
}

export function handleError(error: unknown): void {
  if (error instanceof TimeTrackerError) {
    console.error(chalk.red(`✗ Error: ${error.message}`));
    if (error.code) {
      console.error(chalk.gray(`  Code: ${error.code}`));
    }
  } else if (error instanceof Error) {
    console.error(chalk.red(`✗ Error: ${error.message}`));
  } else {
    console.error(chalk.red('✗ An unknown error occurred'));
  }

  process.exit(1);
}

export function handleWarning(message: string): void {
  console.warn(chalk.yellow(`⚠ Warning: ${message}`));
}

export function handleInfo(message: string): void {
  console.log(chalk.cyan(`ℹ ${message}`));
}

export async function safeExecute<T>(
  operation: () => Promise<T>,
  errorMessage: string = 'Operation failed'
): Promise<T | null> {
  try {
    return await operation();
  } catch (error) {
    if (error instanceof Error) {
      console.error(chalk.red(`${errorMessage}: ${error.message}`));
    } else {
      console.error(chalk.red(errorMessage));
    }
    return null;
  }
}

export function validateTimeEntry(
  startTime: number,
  endTime?: number
): void {
  if (startTime <= 0) {
    throw new ValidationError('Start time must be positive');
  }

  if (endTime !== undefined && endTime <= startTime) {
    throw new ValidationError('End time must be after start time');
  }

  if (endTime !== undefined && endTime > Date.now()) {
    throw new ValidationError('End time cannot be in the future');
  }
}

export function validateProjectName(name: string): void {
  if (!name || name.trim().length === 0) {
    throw new ValidationError('Project name cannot be empty');
  }

  if (name.length > 100) {
    throw new ValidationError('Project name is too long (max 100 characters)');
  }

  if (!/^[a-zA-Z0-9\s-_]+$/.test(name)) {
    throw new ValidationError('Project name contains invalid characters');
  }
}

export function validateDirectoryPath(path: string): void {
  if (!path || path.trim().length === 0) {
    throw new ValidationError('Directory path cannot be empty');
  }
}
