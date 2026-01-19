export interface AnalysisConfig {
  thresholds: Thresholds;
  ignore: string[];
  extensions: string[];
  output: OutputConfig;
}

export interface Thresholds {
  complexity: ComplexityThreshold;
  duplication: DuplicationThreshold;
  maintainability: MaintainabilityThreshold;
  functionLength: LengthThreshold;
  parameterCount: ParameterThreshold;
}

export interface ComplexityThreshold {
  warning: number;
  critical: number;
}

export interface DuplicationThreshold {
  warning: number;
  critical: number;
}

export interface MaintainabilityThreshold {
  warning: number;
  critical: number;
}

export interface LengthThreshold {
  warning: number;
  critical: number;
}

export interface ParameterThreshold {
  warning: number;
  critical: number;
}

export interface OutputConfig {
  format: 'console' | 'json' | 'html' | 'markdown';
  colors: boolean;
  outputFile?: string;
}

export interface AnalysisResult {
  files: FileAnalysis[];
  summary: SummaryMetrics;
  suggestions: Suggestion[];
  config: AnalysisConfig;
}

export interface FileAnalysis {
  path: string;
  language: string;
  metrics: FileMetrics;
  issues: Issue[];
  functions?: FunctionMetrics[];
}

export interface FileMetrics {
  complexity: number;
  maxComplexity: number;
  duplication: number;
  maintainability: number;
  linesOfCode: number;
  functionCount: number;
  averageFunctionLength: number;
}

export interface FunctionMetrics {
  name: string;
  line: number;
  complexity: number;
  length: number;
  parameters: number;
  maintainability: number;
}

export interface SummaryMetrics {
  totalFiles: number;
  totalLinesOfCode: number;
  averageComplexity: number;
  maxComplexity: number;
  averageDuplication: number;
  averageMaintainability: number;
  totalFunctions: number;
  criticalIssues: number;
  warningIssues: number;
  infoIssues: number;
}

export interface Issue {
  type: 'complexity' | 'duplication' | 'maintainability' | 'code-smell';
  severity: 'critical' | 'warning' | 'info';
  message: string;
  line?: number;
  column?: number;
  rule: string;
}

export interface Suggestion {
  type: string;
  priority: 'high' | 'medium' | 'low';
  message: string;
  file?: string;
  line?: number;
  action: string;
}

export interface DuplicationMatch {
  files: string[];
  lines: number[][];
  tokens: number;
  duplicationPercentage: number;
}
