import { Database, ReportOptions, ReportEntry, TimeEntry } from '../types';
import dayjs from 'dayjs';
import Table from 'cli-table3';
import chalk from 'chalk';

export class ReportGenerator {
  constructor(private db: Database) {}

  async generate(options: ReportOptions): Promise<void> {
    const entries = await this.fetchEntries(options);
    const reportEntries = this.processEntries(entries, options);

    switch (options.output_format) {
      case 'table':
        this.printTable(reportEntries, options);
        break;
      case 'json':
        this.printJson(reportEntries);
        break;
      case 'csv':
        this.printCsv(reportEntries);
        break;
      case 'markdown':
        this.printMarkdown(reportEntries, options);
        break;
      default:
        this.printTable(reportEntries, options);
    }
  }

  private async fetchEntries(options: ReportOptions): Promise<TimeEntry[]> {
    let entries: TimeEntry[];

    if (options.start_date && options.end_date) {
      entries = await this.db.getTimeRangeEntries(options.start_date, options.end_date);
    } else {
      entries = await this.db.listTimeEntries();
    }

    // Apply filters
    if (options.project) {
      entries = entries.filter((e) => e.project === options.project);
    }

    if (options.task) {
      entries = entries.filter((e) => e.task === options.task);
    }

    return entries;
  }

  private processEntries(entries: TimeEntry[], options: ReportOptions): ReportEntry[] {
    const reportEntries: ReportEntry[] = [];

    for (const entry of entries) {
      const endTime = entry.end_time || Date.now();
      const duration = endTime - entry.start_time;

      reportEntries.push({
        project: entry.project,
        task: entry.task,
        duration,
        start_time: entry.start_time,
        end_time: endTime,
        notes: entry.notes,
        commit_count: entry.git_commits.length,
      });
    }

    // Group by specified field
    if (options.group_by) {
      return this.groupEntries(reportEntries, options.group_by);
    }

    return reportEntries;
  }

  private groupEntries(entries: ReportEntry[], groupBy: string): ReportEntry[] {
    const groups = new Map<string, ReportEntry[]>();

    for (const entry of entries) {
      let key: string;

      switch (groupBy) {
        case 'project':
          key = entry.project;
          break;
        case 'task':
          key = entry.task || 'No Task';
          break;
        case 'date':
          key = dayjs(entry.start_time).format('YYYY-MM-DD');
          break;
        default:
          key = entry.project;
      }

      if (!groups.has(key)) {
        groups.set(key, []);
      }

      groups.get(key)!.push(entry);
    }

    // Aggregate each group
    const aggregated: ReportEntry[] = [];

    for (const [key, groupEntries] of groups.entries()) {
      const totalDuration = groupEntries.reduce((sum, e) => sum + e.duration, 0);
      const totalCommits = groupEntries.reduce((sum, e) => sum + e.commit_count, 0);

      aggregated.push({
        project: groupBy === 'project' ? key : groupEntries[0].project,
        task: groupBy === 'task' ? key : groupEntries[0].task,
        duration: totalDuration,
        start_time: Math.min(...groupEntries.map((e) => e.start_time)),
        end_time: Math.max(...groupEntries.map((e) => e.end_time)),
        commit_count: totalCommits,
      });
    }

    return aggregated.sort((a, b) => b.duration - a.duration);
  }

  private printTable(entries: ReportEntry[], options: ReportOptions): void {
    if (entries.length === 0) {
      console.log(chalk.gray('No entries found for the given criteria.'));
      return;
    }

    const table = new Table({
      head: [
        chalk.cyan('Project'),
        chalk.cyan('Task'),
        chalk.cyan('Duration'),
        chalk.cyan('Start'),
        chalk.cyan('Commits'),
      ],
      colWidths: [25, 25, 15, 20, 10],
    });

    let totalDuration = 0;
    let totalCommits = 0;

    for (const entry of entries) {
      table.push([
        entry.project,
        entry.task || '-',
        this.formatDuration(entry.duration),
        dayjs(entry.start_time).format('YYYY-MM-DD HH:mm'),
        entry.commit_count.toString(),
      ]);

      totalDuration += entry.duration;
      totalCommits += entry.commit_count;
    }

    console.log(table.toString());
    console.log('');
    console.log(chalk.bold('Summary:'));
    console.log(chalk.cyan(`  Total Duration: ${this.formatDuration(totalDuration)}`));
    console.log(chalk.cyan(`  Total Commits: ${totalCommits}`));
    console.log(chalk.cyan(`  Entries: ${entries.length}`));
  }

  private printJson(entries: ReportEntry[]): void {
    const output = entries.map((entry) => ({
      project: entry.project,
      task: entry.task,
      duration_seconds: Math.round(entry.duration / 1000),
      duration_formatted: this.formatDuration(entry.duration),
      start_time: dayjs(entry.start_time).toISOString(),
      end_time: dayjs(entry.end_time).toISOString(),
      notes: entry.notes,
      commit_count: entry.commit_count,
    }));

    console.log(JSON.stringify(output, null, 2));
  }

  private printCsv(entries: ReportEntry[]): void {
    console.log('Project,Task,Duration,Start Time,End Time,Notes,Commits');

    for (const entry of entries) {
      const row = [
        entry.project,
        entry.task || '',
        this.formatDuration(entry.duration),
        dayjs(entry.start_time).toISOString(),
        dayjs(entry.end_time).toISOString(),
        entry.notes || '',
        entry.commit_count.toString(),
      ];
      console.log(row.join(','));
    }
  }

  private printMarkdown(entries: ReportEntry[], options: ReportOptions): void {
    console.log('# Time Report\n');
    console.log(`**Period:** ${dayjs(options.start_date).format('YYYY-MM-DD')} to ${dayjs(options.end_date).format('YYYY-MM-DD')}\n\n`);
    console.log('## Entries\n\n');
    console.log('| Project | Task | Duration | Start | Commits |');
    console.log('|---------|------|----------|-------|---------|');

    for (const entry of entries) {
      console.log(
        `| ${entry.project} | ${entry.task || '-'} | ${this.formatDuration(entry.duration)} | ${dayjs(
          entry.start_time
        ).format('YYYY-MM-DD HH:mm')} | ${entry.commit_count} |`
      );
    }

    const totalDuration = entries.reduce((sum, e) => sum + e.duration, 0);
    const totalCommits = entries.reduce((sum, e) => sum + e.commit_count, 0);

    console.log('\n## Summary\n\n');
    console.log(`- **Total Duration:** ${this.formatDuration(totalDuration)}`);
    console.log(`- **Total Commits:** ${totalCommits}`);
    console.log(`- **Entries:** ${entries.length}`);
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
