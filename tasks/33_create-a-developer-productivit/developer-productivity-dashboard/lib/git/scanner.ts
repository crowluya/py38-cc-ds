import simpleGit, { SimpleGit } from 'simple-git';
import { promises as fs } from 'fs';
import path from 'path';
import { RepositoryInfo } from './types';

export class GitScanner {
  private git: SimpleGit;

  constructor(repoPath: string) {
    this.git = simpleGit(repoPath);
  }

  static async validateRepository(repoPath: string): Promise<boolean> {
    try {
      const git = simpleGit(repoPath);
      await git.revparse(['--is-inside-work-tree']);
      return true;
    } catch {
      return false;
    }
  }

  async getRepositoryInfo(): Promise<RepositoryInfo> {
    const repoPath = this.git.cwd();
    const name = path.basename(repoPath);
    const branchData = await this.git.branch();
    const lastCommit = await this.git.log({ maxCount: 1 });

    return {
      path: repoPath,
      name,
      branch: branchData.current || 'HEAD',
      lastCommit: lastCommit.latest?.hash,
    };
  }

  async getBranches(): Promise<string[]> {
    const branches = await this.git.branch();
    return Object.keys(branches.branches);
  }

  async getAuthors(): Promise<string[]> {
    const log = await this.git.log({ maxCount: 10000 });
    const authors = new Set(log.all.map(commit => commit.author_name));
    return Array.from(authors);
  }
}
