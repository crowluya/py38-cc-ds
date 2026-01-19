import * as fs from 'fs';
import * as path from 'path';
import { AnalysisConfig } from '../types';

const DEFAULT_CONFIG: AnalysisConfig = {
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

export function loadConfig(configPath?: string): AnalysisConfig {
  let config = { ...DEFAULT_CONFIG };

  if (configPath) {
    if (fs.existsSync(configPath)) {
      try {
        const userConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        config = mergeConfig(config, userConfig);
      } catch (error) {
        console.warn(`Warning: Could not parse config file at ${configPath}`);
      }
    } else {
      console.warn(`Warning: Config file not found at ${configPath}`);
    }
  } else {
    // Try to find .codequalityrc.json in current directory
    const defaultPaths = [
      '.codequalityrc.json',
      '.codequalityrc',
      'codequality.config.json'
    ];

    for (const defaultPath of defaultPaths) {
      if (fs.existsSync(defaultPath)) {
        try {
          const userConfig = JSON.parse(fs.readFileSync(defaultPath, 'utf-8'));
          config = mergeConfig(config, userConfig);
          break;
        } catch (error) {
          // Continue to next path
        }
      }
    }
  }

  return config;
}

function mergeConfig(base: AnalysisConfig, override: any): AnalysisConfig {
  return {
    thresholds: { ...base.thresholds, ...override.thresholds },
    ignore: override.ignore || base.ignore,
    extensions: override.extensions || base.extensions,
    output: { ...base.output, ...override.output }
  };
}

export function validateConfig(config: AnalysisConfig): boolean {
  if (!config.thresholds || !config.ignore || !config.extensions || !config.output) {
    return false;
  }

  const validFormats = ['console', 'json', 'html', 'markdown'];
  if (!validFormats.includes(config.output.format)) {
    return false;
  }

  return true;
}
