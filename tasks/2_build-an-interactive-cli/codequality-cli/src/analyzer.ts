import * as fs from 'fs';
import * as path from 'path';
import chalk from 'chalk';
import { FileDiscoverer } from './utils/fileDiscovery';
import { JavaScriptParser } from './parsers/javascriptParser';
import { DuplicationAnalyzer } from './analyzers/duplicationAnalyzer';
import { ConsoleReporter } from './reporters/consoleReporter';
import { JsonReporter } from './reporters/jsonReporter';
import { AnalysisConfig, AnalysisResult, FileAnalysis, SummaryMetrics, Issue, Suggestion } from './types';

export async function analyzeProject(
  rootPath: string,
  config: AnalysisConfig,
  verbose: boolean = false
): Promise<AnalysisResult | null> {
  const startTime = Date.now();

  try {
    // Resolve root path
    const resolvedPath = path.resolve(rootPath);
    if (!fs.existsSync(resolvedPath)) {
      console.error(chalk.red(`Error: Path does not exist: ${resolvedPath}`));
      return null;
    }

    // Discover files
    if (verbose) {
      console.log(chalk.gray('Discovering files...'));
    }

    const discoverer = new FileDiscoverer({
      extensions: config.extensions,
      ignore: config.ignore,
      rootPath: resolvedPath
    });

    const files = await discoverer.discoverFiles();

    if (files.length === 0) {
      console.warn(chalk.yellow('No files found to analyze.'));
      return null;
    }

    if (verbose) {
      console.log(chalk.gray(`Found ${files.length} files to analyze\n`));
    }

    // Read all file contents
    const fileContents = new Map<string, string>();
    for (const file of files) {
      try {
        const content = await fs.promises.readFile(file, 'utf-8');
        fileContents.set(file, content);
      } catch (error) {
        if (verbose) {
          console.warn(chalk.yellow(`Warning: Could not read file: ${file}`));
        }
      }
    }

    // Analyze duplication across all files
    if (verbose) {
      console.log(chalk.gray('Analyzing code duplication...'));
    }

    const duplicationAnalyzer = new DuplicationAnalyzer();
    const duplicates = duplicationAnalyzer.analyze(fileContents);

    // Analyze each file
    const fileAnalyses: FileAnalysis[] = [];
    let progress = 0;

    for (const file of files) {
      progress++;
      if (verbose && progress % 10 === 0) {
        process.stdout.write(`\r${chalk.gray(`Analyzing... ${progress}/${files.length}`)}`);
      }

      const content = fileContents.get(file);
      if (!content) continue;

      const language = FileDiscoverer.getFileLanguage(file);
      const analysis = await analyzeFile(file, content, language, config, duplicates);
      fileAnalyses.push(analysis);
    }

    if (verbose) {
      process.stdout.write(`\r${chalk.gray(`Analyzed ${files.length} files`)}\n`);
    }

    // Calculate summary metrics
    const summary = calculateSummary(fileAnalyses);

    // Generate suggestions
    const suggestions = generateSuggestions(fileAnalyses, config);

    const result: AnalysisResult = {
      files: fileAnalyses,
      summary,
      suggestions,
      config
    };

    // Generate report
    const reporter = config.output.format === 'json'
      ? new JsonReporter()
      : new ConsoleReporter(config.output.colors);

    reporter.generateReport(result);

    // Write to file if specified
    if (config.output.outputFile) {
      const outputReporter = config.output.format === 'json'
        ? new JsonReporter()
        : new ConsoleReporter(false);
      const report = outputReporter.generateReport(result);
      await fs.promises.writeFile(config.output.outputFile, report);
      console.log(chalk.green(`\nReport saved to: ${config.output.outputFile}`));
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(chalk.gray(`\nCompleted in ${duration}s\n`));

    return result;

  } catch (error) {
    console.error(chalk.red('Error during analysis:'));
    console.error(error);
    return null;
  }
}

async function analyzeFile(
  filePath: string,
  content: string,
  language: string,
  config: AnalysisConfig,
  duplicates: any[]
): Promise<FileAnalysis> {
  const issues: Issue[] = [];
  let metrics: any;
  let functions: any[] = [];

  // Parse based on language
  if (language === 'javascript' || language === 'typescript') {
    const parser = new JavaScriptParser(content, filePath);
    const result = parser.parse();
    metrics = result.metrics;
    functions = result.functions;

    // Calculate duplication for this file
    metrics.duplication = 0;
    for (const duplicate of duplicates) {
      if (duplicate.files.includes(filePath)) {
        metrics.duplication += duplicate.tokens;
      }
    }

    // Calculate maintainability
    metrics.maintainability = calculateMaintainability(metrics);

    // Generate issues
    issues.push(...generateComplexityIssues(filePath, result, config));
    issues.push(...generateFunctionLengthIssues(filePath, result, config));
    issues.push(...generateParameterCountIssues(filePath, result, config));
    issues.push(...generateMaintainabilityIssues(filePath, metrics, config));
  } else {
    // For unsupported languages, provide basic metrics
    const lines = content.split('\n').length;
    metrics = {
      complexity: 0,
      maxComplexity: 0,
      duplication: 0,
      maintainability: 100,
      linesOfCode: lines,
      functionCount: 0,
      averageFunctionLength: 0
    };
  }

  return {
    path: filePath,
    language,
    metrics,
    issues,
    functions
  };
}

function calculateMaintainability(metrics: any): number {
  // Simplified maintainability index
  const cc = metrics.complexity;
  const loc = metrics.linesOfCode;
  const volume = loc; // Simplified

  const mi = Math.max(0, 171 - 5.2 * Math.log(volume + 1) - 0.23 * cc - 16.2 * Math.log(loc + 1));
  return Math.round((mi / 171) * 100);
}

function generateComplexityIssues(filePath: string, result: any, config: AnalysisConfig): Issue[] {
  const issues: Issue[] = [];

  for (const func of result.functions) {
    if (func.complexity >= config.thresholds.complexity.critical) {
      issues.push({
        type: 'complexity',
        severity: 'critical',
        message: `Function '${func.name}' has high cyclomatic complexity (${func.complexity})`,
        line: func.line,
        rule: 'high-complexity'
      });
    } else if (func.complexity >= config.thresholds.complexity.warning) {
      issues.push({
        type: 'complexity',
        severity: 'warning',
        message: `Function '${func.name}' has moderate cyclomatic complexity (${func.complexity})`,
        line: func.line,
        rule: 'moderate-complexity'
      });
    }
  }

  return issues;
}

function generateFunctionLengthIssues(filePath: string, result: any, config: AnalysisConfig): Issue[] {
  const issues: Issue[] = [];

  for (const func of result.functions) {
    if (func.length >= config.thresholds.functionLength.critical) {
      issues.push({
        type: 'code-smell',
        severity: 'critical',
        message: `Function '${func.name}' is too long (${func.length} lines)`,
        line: func.line,
        rule: 'long-function'
      });
    } else if (func.length >= config.thresholds.functionLength.warning) {
      issues.push({
        type: 'code-smell',
        severity: 'warning',
        message: `Function '${func.name}' is moderately long (${func.length} lines)`,
        line: func.line,
        rule: 'moderate-long-function'
      });
    }
  }

  return issues;
}

function generateParameterCountIssues(filePath: string, result: any, config: AnalysisConfig): Issue[] {
  const issues: Issue[] = [];

  for (const func of result.functions) {
    if (func.parameters >= config.thresholds.parameterCount.critical) {
      issues.push({
        type: 'code-smell',
        severity: 'critical',
        message: `Function '${func.name}' has too many parameters (${func.parameters})`,
        line: func.line,
        rule: 'too-many-parameters'
      });
    } else if (func.parameters >= config.thresholds.parameterCount.warning) {
      issues.push({
        type: 'code-smell',
        severity: 'warning',
        message: `Function '${func.name}' has many parameters (${func.parameters})`,
        line: func.line,
        rule: 'many-parameters'
      });
    }
  }

  return issues;
}

function generateMaintainabilityIssues(filePath: string, metrics: any, config: AnalysisConfig): Issue[] {
  const issues: Issue[] = [];

  if (metrics.maintainability <= config.thresholds.maintainability.critical) {
    issues.push({
      type: 'maintainability',
      severity: 'critical',
      message: `File has low maintainability index (${metrics.maintainability})`,
      rule: 'low-maintainability'
    });
  } else if (metrics.maintainability <= config.thresholds.maintainability.warning) {
    issues.push({
      type: 'maintainability',
      severity: 'warning',
      message: `File has moderate maintainability index (${metrics.maintainability})`,
      rule: 'moderate-maintainability'
    });
  }

  return issues;
}

function calculateSummary(fileAnalyses: FileAnalysis[]): SummaryMetrics {
  const totalFiles = fileAnalyses.length;
  const totalLinesOfCode = fileAnalyses.reduce((sum, f) => sum + f.metrics.linesOfCode, 0);
  const totalFunctions = fileAnalyses.reduce((sum, f) => sum + f.metrics.functionCount, 0);

  const complexities = fileAnalyses.map(f => f.metrics.complexity).filter(c => c > 0);
  const averageComplexity = complexities.length > 0
    ? complexities.reduce((sum, c) => sum + c, 0) / complexities.length
    : 0;

  const maxComplexity = fileAnalyses.reduce((max, f) => Math.max(max, f.metrics.maxComplexity), 0);

  const duplications = fileAnalyses.map(f => f.metrics.duplication);
  const averageDuplication = duplications.length > 0
    ? duplications.reduce((sum, d) => sum + d, 0) / duplications.length
    : 0;

  const maintainabilities = fileAnalyses.map(f => f.metrics.maintainability).filter(m => m > 0);
  const averageMaintainability = maintainabilities.length > 0
    ? maintainabilities.reduce((sum, m) => sum + m, 0) / maintainabilities.length
    : 0;

  let criticalIssues = 0;
  let warningIssues = 0;
  let infoIssues = 0;

  for (const analysis of fileAnalyses) {
    for (const issue of analysis.issues) {
      if (issue.severity === 'critical') criticalIssues++;
      else if (issue.severity === 'warning') warningIssues++;
      else infoIssues++;
    }
  }

  return {
    totalFiles,
    totalLinesOfCode,
    averageComplexity: Math.round(averageComplexity * 100) / 100,
    maxComplexity,
    averageDuplication: Math.round(averageDuplication * 100) / 100,
    averageMaintainability: Math.round(averageMaintainability),
    totalFunctions,
    criticalIssues,
    warningIssues,
    infoIssues
  };
}

function generateSuggestions(fileAnalyses: FileAnalysis[], config: AnalysisConfig): Suggestion[] {
  const suggestions: Suggestion[] = [];

  // Analyze patterns and generate actionable suggestions
  const highComplexityFiles = fileAnalyses.filter(f => f.metrics.complexity > config.thresholds.complexity.warning);
  if (highComplexityFiles.length > 0) {
    suggestions.push({
      type: 'complexity',
      priority: 'high',
      message: `${highComplexityFiles.length} file(s) have high complexity`,
      action: 'Consider breaking down complex functions into smaller, more manageable units'
    });
  }

  const lowMaintainabilityFiles = fileAnalyses.filter(f => f.metrics.maintainability < config.thresholds.maintainability.warning);
  if (lowMaintainabilityFiles.length > 0) {
    suggestions.push({
      type: 'maintainability',
      priority: 'high',
      message: `${lowMaintainabilityFiles.length} file(s) have low maintainability`,
      action: 'Refactor code to improve readability and reduce complexity'
    });
  }

  const longFunctions = fileAnalyses.flatMap(f => f.functions?.filter(func => func.length > config.thresholds.functionLength.warning) || []);
  if (longFunctions.length > 0) {
    suggestions.push({
      type: 'code-smell',
      priority: 'medium',
      message: `${longFunctions.length} function(s) are too long`,
      action: 'Break long functions into smaller, single-purpose functions'
    });
  }

  const manyParamFunctions = fileAnalyses.flatMap(f => f.functions?.filter(func => func.parameters > config.thresholds.parameterCount.warning) || []);
  if (manyParamFunctions.length > 0) {
    suggestions.push({
      type: 'code-smell',
      priority: 'medium',
      message: `${manyParamFunctions.length} function(s) have too many parameters`,
      action: 'Consider using objects to group related parameters'
    });
  }

  return suggestions;
}
