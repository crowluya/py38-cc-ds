#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { analyzeProject } from './analyzer';
import { loadConfig } from './utils/config';
import { AnalysisConfig } from './types';

const program = new Command();

program
  .name('codequality')
  .description('Interactive CLI tool for code quality analysis')
  .version('1.0.0');

program
  .command('analyze')
  .description('Analyze code quality of a project')
  .argument('[path]', 'Path to the project directory', '.')
  .option('-c, --config <path>', 'Path to configuration file')
  .option('-o, --output <format>', 'Output format: console, json, html, markdown', 'console')
  .option('-f, --output-file <path>', 'Write output to file')
  .option('-e, --extensions <exts>', 'Comma-separated list of file extensions to analyze')
  .option('-i, --ignore <patterns>', 'Comma-separated list of ignore patterns')
  .option('--no-colors', 'Disable colored output')
  .option('-v, --verbose', 'Verbose output')
  .action(async (path: string, options) => {
    try {
      // Load configuration
      let config: AnalysisConfig = loadConfig(options.config);

      // Override config with CLI options
      if (options.output) {
        config.output.format = options.output as any;
      }
      if (options.outputFile) {
        config.output.outputFile = options.outputFile;
      }
      if (options.colors === false) {
        config.output.colors = false;
      }
      if (options.extensions) {
        config.extensions = options.extensions.split(',').map((e: string) => e.trim());
      }
      if (options.ignore) {
        config.ignore = [
          ...config.ignore,
          ...options.ignore.split(',').map((p: string) => p.trim())
        ];
      }

      console.log(chalk.bold.blue('\n🔍 Code Quality Analysis\n'));

      const result = await analyzeProject(path, config, options.verbose);

      if (result) {
        console.log(chalk.bold.green('\n✅ Analysis complete!\n'));
      }
    } catch (error) {
      console.error(chalk.red('❌ Error during analysis:'));
      console.error(error);
      process.exit(1);
    }
  });

program
  .command('init')
  .description('Initialize configuration file')
  .option('-f, --force', 'Overwrite existing configuration')
  .action((options) => {
    const fs = require('fs');
    const configPath = '.codequalityrc.json';

    if (fs.existsSync(configPath) && !options.force) {
      console.log(chalk.yellow(`Configuration file already exists at ${configPath}`));
      console.log(chalk.gray('Use --force to overwrite'));
      return;
    }

    const defaultConfig = {
      thresholds: {
        complexity: { warning: 10, critical: 20 },
        duplication: { warning: 5, critical: 10 },
        maintainability: { warning: 50, critical: 30 },
        functionLength: { warning: 50, critical: 100 },
        parameterCount: { warning: 5, critical: 8 }
      },
      ignore: [
        'node_modules/**',
        'dist/**',
        'build/**',
        'coverage/**',
        '**/*.min.js',
        '**/*.bundle.js'
      ],
      extensions: ['.js', '.jsx', '.ts', '.tsx', '.mjs'],
      output: {
        format: 'console',
        colors: true
      }
    };

    fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
    console.log(chalk.green(`✅ Configuration file created at ${configPath}`));
  });

program
  .command('config')
  .description('Show current configuration')
  .option('-c, --config <path>', 'Path to configuration file')
  .action((options) => {
    const config = loadConfig(options.config);
    console.log(JSON.stringify(config, null, 2));
  });

program.parse();
