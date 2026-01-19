import simpleGit, { SimpleGit } from 'simple-git';
import { Database, GitCommit, TimeEntry } from '../types';
import path from 'path';
import fs from 'fs';
import dayjs from 'dayjs';

export class GitIntegration {
  private git: SimpleGit;

  constructor(private db: Database) {
    this.git = simpleGit();
  }

  async syncCommits(): Promise<void> {
    const projects = await this.db.listProjects();

    for (const project of projects) {
      for (const repoPath of project.git_repos) {
        try {
          await this.syncRepository(repoPath, project.id);
        } catch (error) {
          console.error(`Error syncing repo ${repoPath}:`, error);
        }
      }
    }

    // Also sync current directory if it's a git repo
    const currentDir = process.cwd();
    if (await this.isGitRepository(currentDir)) {
      await this.syncRepository(currentDir);
    }
  }

  async syncRepository(repoPath: string, projectId?: string): Promise<void> {
    const git = simpleGit(repoPath);
    const log = await git.log({ maxCount: 100 });

    for (const commit of log.all) {
      const gitCommit: Omit<GitCommit, 'time_entry_id'> = {
        hash: commit.hash,
        timestamp: commit.date ? new Date(commit.date).getTime() : Date.now(),
        message: commit.message,
        author: commit.author_name,
        repository: repoPath,
      };

      try {
        // Check if commit already exists
        // For now, we'll just insert (in production, check for duplicates)
        await this.storeCommit(gitCommit);
      } catch (error) {
        // Commit might already exist, skip
      }
    }

    // Match commits to time entries
    await this.matchCommitsToTimeEntries(repoPath);
  }

  async matchCommitsToTimeEntries(repoPath: string): Promise<void> {
    const git = simpleGit(repoPath);
    const log = await git.log({ maxCount: 100 });
    const entries = await this.db.listTimeEntries();

    for (const commit of log.all) {
      const commitTime = commit.date ? new Date(commit.date).getTime() : Date.now();

      // Find overlapping time entries
      for (const entry of entries) {
        if (entry.status !== 'completed') continue;

        const entryStart = entry.start_time;
        const entryEnd = entry.end_time!;

        // Check if commit was made during the time entry
        if (commitTime >= entryStart && commitTime <= entryEnd) {
          // Link commit to time entry
          if (!entry.git_commits.includes(commit.hash)) {
            entry.git_commits.push(commit.hash);
            await this.db.updateTimeEntry(entry.id, {
              git_commits: entry.git_commits,
            });
          }

          // Also update the commit record
          await this.db.linkCommitToTimeEntry(commit.hash, entry.id);
        }
      }
    }
  }

  async getCurrentBranch(): Promise<string> {
    try {
      const branch = await this.git.branch();
      return branch.current || 'main';
    } catch {
      return 'unknown';
    }
  }

  async getCurrentCommit(): Promise<string> {
    try {
      const log = await this.git.log({ maxCount: 1 });
      return log.latest?.hash || '';
    } catch {
      return '';
    }
  }

  async getRecentCommits(count: number = 10): Promise<GitCommit[]> {
    try {
      const repo = process.cwd();
      const git = simpleGit(repo);
      const log = await git.log({ maxCount: count });

      return log.all.map((commit) => ({
        hash: commit.hash,
        timestamp: commit.date ? new Date(commit.date).getTime() : Date.now(),
        message: commit.message,
        author: commit.author_name,
        repository: repo,
      }));
    } catch {
      return [];
    }
  }

  async isGitRepository(dirPath: string): Promise<boolean> {
    const gitDir = path.join(dirPath, '.git');
    return fs.existsSync(gitDir);
  }

  async getGitRoot(): Promise<string | null> {
    try {
      const root = await this.git.revparse(['--show-toplevel']);
      return root || null;
    } catch {
      return null;
    }
  }

  async annotateCommitMessage(originalMessage: string, timeEntryId: string): Promise<string> {
    return `${originalMessage}\n\n[tracked with timetracker: ${timeEntryId}]`;
  }

  async setupGitHook(): Promise<void> {
    const gitRoot = await this.getGitRoot();
    if (!gitRoot) {
      throw new Error('Not in a git repository');
    }

    const hooksDir = path.join(gitRoot, '.git', 'hooks');
    const postCommitHook = path.join(hooksDir, 'post-commit');

    // Create hooks directory if it doesn't exist
    if (!fs.existsSync(hooksDir)) {
      fs.mkdirSync(hooksDir, { recursive: true });
    }

    // Create post-commit hook
    const hookContent = `#!/bin/bash
# Track time for this commit
track git-sync
`;

    fs.writeFileSync(postCommitHook, hookContent, { mode: 0o755 });
    console.log('✓ Git hook installed successfully');
  }

  private async storeCommit(commit: Omit<GitCommit, 'time_entry_id'>): Promise<void> {
    // This would insert into the git_commits table
    // For now, it's handled by the matchCommitsToTimeEntries method
  }

  formatCommitMessage(message: string, maxLength: number = 50): string {
    if (message.length <= maxLength) {
      return message;
    }
    return message.substring(0, maxLength - 3) + '...';
  }
}
