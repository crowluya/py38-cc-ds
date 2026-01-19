import chalk from 'chalk';
import Table from 'cli-table3';
import { AnalysisResult } from '../types';

export class ConsoleReporter {
  private useColors: boolean;

  constructor(useColors: boolean = true) {
    this.useColors = useColors;
  }

  generateReport(result: AnalysisResult): string {
    this.printSummary(result);
    this.printTopIssues(result);
    this.printSuggestions(result);
    this.printFileDetails(result);

    return '';
  }

  private printSummary(result: AnalysisResult): void {
    const { summary } = result;

    console.log(chalk.bold('📊 Summary'));
    console.log('─────────────────────────────────────');

    const table = new Table({
      colWidths: [25, 15],
      style: {
        head: [],
        border: this.useColors ? ['grey'] : []
      }
    });

    table.push(
      ['Files Analyzed', summary.totalFiles.toString()],
      ['Lines of Code', summary.totalLinesOfCode.toString()],
      ['Functions', summary.totalFunctions.toString()],
      ['Avg Complexity', summary.averageComplexity.toFixed(2)],
      ['Max Complexity', summary.maxComplexity.toString()],
      ['Avg Maintainability', `${summary.averageMaintainability}%`],
      [chalk.red('Critical Issues'), summary.criticalIssues.toString()],
      [chalk.yellow('Warnings'), summary.warningIssues.toString()],
      [chalk.blue('Info'), summary.infoIssues.toString()]
    );

    console.log(table.toString());
    console.log('');
  }

  private printTopIssues(result: AnalysisResult): void {
    const allIssues = result.files.flatMap(f =>
      f.issues.map(issue => ({ ...issue, file: f.path }))
    );

    const criticalIssues = allIssues.filter(i => i.severity === 'critical').slice(0, 10);
    const warningIssues = allIssues.filter(i => i.severity === 'warning').slice(0, 10);

    if (criticalIssues.length > 0) {
      console.log(chalk.bold.red('🚨 Critical Issues'));
      console.log('─────────────────────────────────────');

      for (const issue of criticalIssues) {
        const fileName = issue.file.split('/').pop() || issue.file;
        console.log(chalk.red(`  ✗ ${fileName}:${issue.line || '?'} - ${issue.message}`));
      }
      console.log('');
    }

    if (warningIssues.length > 0) {
      console.log(chalk.bold.yellow('⚠️  Warnings'));
      console.log('─────────────────────────────────────');

      for (const issue of warningIssues) {
        const fileName = issue.file.split('/').pop() || issue.file;
        console.log(chalk.yellow(`  ⚠ ${fileName}:${issue.line || '?'} - ${issue.message}`));
      }
      console.log('');
    }
  }

  private printSuggestions(result: AnalysisResult): void {
    if (result.suggestions.length === 0) {
      return;
    }

    console.log(chalk.bold('💡 Suggestions'));
    console.log('─────────────────────────────────────');

    for (const suggestion of result.suggestions) {
      const priorityIcon = suggestion.priority === 'high' ? '🔴' : suggestion.priority === 'medium' ? '🟡' : '🟢';
      console.log(`${priorityIcon} ${suggestion.message}`);
      console.log(chalk.gray(`   Action: ${suggestion.action}`));
      console.log('');
    }
  }

  private printFileDetails(result: AnalysisResult): void {
    const problematicFiles = result.files
      .filter(f => f.issues.length > 0)
      .sort((a, b) => b.issues.length - a.issues.length)
      .slice(0, 20);

    if (problematicFiles.length === 0) {
      console.log(chalk.bold.green('✅ No issues found!'));
      return;
    }

    console.log(chalk.bold('\n📁 Most Problematic Files'));
    console.log('─────────────────────────────────────');

    const table = new Table({
      head: [chalk.gray('File'), chalk.gray('Issues'), chalk.gray('Complexity'), chalk.gray('Maintainability')],
      colWidths: [40, 10, 12, 15],
      style: {
        head: [],
        border: this.useColors ? ['grey'] : []
      }
    });

    for (const file of problematicFiles) {
      const fileName = file.path.split('/').pop() || file.path;
      const complexity = file.metrics.complexity > result.config.thresholds.complexity.warning
        ? chalk.red(file.metrics.complexity.toFixed(1))
        : chalk.green(file.metrics.complexity.toFixed(1));

      const maintainability = file.metrics.maintainability < result.config.thresholds.maintainability.warning
        ? chalk.red(`${file.metrics.maintainability}%`)
        : chalk.green(`${file.metrics.maintainability}%`);

      const issues = file.issues.filter(i => i.severity === 'critical').length > 0
        ? chalk.red(file.issues.length.toString())
        : chalk.yellow(file.issues.length.toString());

      table.push([fileName, issues, complexity, maintainability]);
    }

    console.log(table.toString());
    console.log('');
  }
}
