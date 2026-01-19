import simpleGit, { SimpleGit, LogOptions } from 'simple-git';
import { Commit, AnalysisOptions } from './types';

export class GitLogParser {
  private git: SimpleGit;

  constructor(repoPath: string) {
    this.git = simpleGit(repoPath);
  }

  async parseCommits(options?: AnalysisOptions): Promise<Commit[]> {
    const logOptions: LogOptions = {
      maxCount: 10000,
      format: {
        hash: '%H',
        author_name: '%an',
        author_email: '%ae',
        date: '%ai',
        message: '%s',
      },
    };

    if (options?.since) {
      logOptions.from = options.since;
    }

    if (options?.until) {
      logOptions.to = options.until;
    }

    if (options?.author) {
      logOptions.author = options.author;
    }

    const log = await this.git.log(logOptions);
    const commits: Commit[] = [];

    for (const commit of log.all) {
      const fileStats = await this.getCommitStats(commit.hash);

      commits.push({
        hash: commit.hash,
        author: commit.author_name,
        email: commit.author_email,
        date: new Date(commit.date),
        message: commit.message,
        files: fileStats.files,
        insertions: fileStats.insertions,
        deletions: fileStats.deletions,
      });
    }

    return commits;
  }

  private async getCommitStats(hash: string): Promise<{
    files: string[];
    insertions: number;
    deletions: number;
  }> {
    try {
      const diff = await this.git.show([hash, '--format=', '--numstat']);
      const lines = diff.split('\n').filter(line => line.trim());

      let insertions = 0;
      let deletions = 0;
      const files: string[] = [];

      lines.forEach(line => {
        const parts = line.split('\t');
        if (parts.length >= 3) {
          const added = parseInt(parts[0]) || 0;
          const deleted = parseInt(parts[1]) || 0;
          insertions += added;
          deletions += deleted;
          files.push(parts[2]);
        }
      });

      return { files, insertions, deletions };
    } catch {
      return { files: [], insertions: 0, deletions: 0 };
    }
  }
}

// Language detection based on file extensions
export const LANGUAGE_MAP: Record<string, string> = {
  '.ts': 'TypeScript',
  '.tsx': 'TypeScript',
  '.js': 'JavaScript',
  '.jsx': 'JavaScript',
  '.py': 'Python',
  '.java': 'Java',
  '.cpp': 'C++',
  '.c': 'C',
  '.cs': 'C#',
  '.go': 'Go',
  '.rs': 'Rust',
  '.php': 'PHP',
  '.rb': 'Ruby',
  '.swift': 'Swift',
  '.kt': 'Kotlin',
  '.scala': 'Scala',
  '.html': 'HTML',
  '.css': 'CSS',
  '.scss': 'SCSS',
  '.sass': 'Sass',
  '.less': 'Less',
  '.json': 'JSON',
  '.xml': 'XML',
  '.yaml': 'YAML',
  '.yml': 'YAML',
  '.md': 'Markdown',
  '.sh': 'Shell',
  '.sql': 'SQL',
  '.r': 'R',
  '.m': 'Matlab',
  '.vue': 'Vue',
  '.svelte': 'Svelte',
};

export function detectLanguage(filename: string): string {
  const ext = filename.includes('.')
    ? '.' + filename.split('.').pop()?.toLowerCase()
    : '';

  return LANGUAGE_MAP[ext] || 'Other';
}
