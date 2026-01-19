export interface Commit {
  hash: string;
  author: string;
  email: string;
  date: Date;
  message: string;
  files: string[];
  insertions: number;
  deletions: number;
}

export interface GitMetrics {
  totalCommits: number;
  totalAuthors: number;
  commitFrequency: {
    date: string;
    count: number;
  }[];
  languageDistribution: {
    language: string;
    files: number;
    percentage: number;
  }[];
  hourlyActivity: {
    hour: number;
    day: number;
    count: number;
  }[];
  velocity: {
    date: string;
    commits: number;
    lines: number;
  }[];
  topContributors: {
    author: string;
    commits: number;
    linesChanged: number;
  }[];
  topFiles: {
    file: string;
    commits: number;
    linesChanged: number;
  }[];
}

export interface RepositoryInfo {
  path: string;
  name: string;
  branch: string;
  lastCommit?: string;
}

export interface AnalysisOptions {
  since?: string;
  until?: string;
  author?: string;
  branch?: string;
}
