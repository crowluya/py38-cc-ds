import { Commit, GitMetrics } from './types';
import { detectLanguage } from './parser';

export function calculateMetrics(commits: Commit[]): GitMetrics {
  const totalCommits = commits.length;
  const authors = new Set(commits.map(c => c.author));

  // Commit frequency (group by day)
  const commitFrequencyMap = new Map<string, number>();
  commits.forEach(commit => {
    const date = commit.date.toISOString().split('T')[0];
    commitFrequencyMap.set(date, (commitFrequencyMap.get(date) || 0) + 1);
  });

  const commitFrequency = Array.from(commitFrequencyMap.entries())
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date));

  // Language distribution
  const languageFiles = new Map<string, string[]>();
  commits.forEach(commit => {
    commit.files.forEach(file => {
      const language = detectLanguage(file);
      if (!languageFiles.has(language)) {
        languageFiles.set(language, []);
      }
      languageFiles.get(language)!.push(file);
    });
  });

  const totalFiles = Array.from(languageFiles.values()).flat().length;
  const languageDistribution = Array.from(languageFiles.entries())
    .map(([language, files]) => ({
      language,
      files: files.length,
      percentage: totalFiles > 0 ? (files.length / totalFiles) * 100 : 0,
    }))
    .sort((a, b) => b.files - a.files)
    .slice(0, 10);

  // Hourly activity heatmap (day 0-6, hour 0-23)
  const hourlyActivityMap = new Map<string, number>();
  commits.forEach(commit => {
    const day = commit.date.getDay();
    const hour = commit.date.getHours();
    const key = `${day}-${hour}`;
    hourlyActivityMap.set(key, (hourlyActivityMap.get(key) || 0) + 1);
  });

  const hourlyActivity: { hour: number; day: number; count: number }[] = [];
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const key = `${day}-${hour}`;
      hourlyActivity.push({
        day,
        hour,
        count: hourlyActivityMap.get(key) || 0,
      });
    }
  }

  // Velocity (commits and lines over time)
  const velocityMap = new Map<string, { commits: number; lines: number }>();
  commits.forEach(commit => {
    const date = commit.date.toISOString().split('T')[0];
    const current = velocityMap.get(date) || { commits: 0, lines: 0 };
    velocityMap.set(date, {
      commits: current.commits + 1,
      lines: current.lines + commit.insertions + commit.deletions,
    });
  });

  const velocity = Array.from(velocityMap.entries())
    .map(([date, data]) => ({
      date,
      commits: data.commits,
      lines: data.lines,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  // Top contributors
  const contributorMap = new Map<string, { commits: number; lines: number }>();
  commits.forEach(commit => {
    const current = contributorMap.get(commit.author) || { commits: 0, lines: 0 };
    contributorMap.set(commit.author, {
      commits: current.commits + 1,
      lines: current.lines + commit.insertions + commit.deletions,
    });
  });

  const topContributors = Array.from(contributorMap.entries())
    .map(([author, data]) => ({
      author,
      commits: data.commits,
      linesChanged: data.lines,
    }))
    .sort((a, b) => b.commits - a.commits)
    .slice(0, 10);

  // Top files
  const fileMap = new Map<string, { commits: number; lines: number }>();
  commits.forEach(commit => {
    commit.files.forEach(file => {
      const current = fileMap.get(file) || { commits: 0, lines: 0 };
      fileMap.set(file, {
        commits: current.commits + 1,
        lines: current.lines + commit.insertions + commit.deletions,
      });
    });
  });

  const topFiles = Array.from(fileMap.entries())
    .map(([file, data]) => ({
      file,
      commits: data.commits,
      linesChanged: data.lines,
    }))
    .sort((a, b) => b.commits - a.commits)
    .slice(0, 10);

  return {
    totalCommits,
    totalAuthors: authors.size,
    commitFrequency,
    languageDistribution,
    hourlyActivity,
    velocity,
    topContributors,
    topFiles,
  };
}
