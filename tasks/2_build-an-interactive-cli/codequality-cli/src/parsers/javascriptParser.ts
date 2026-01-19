import * as parser from '@babel/parser';
import traverse from '@babel/traverse';
import * as t from '@babel/types';
import { FunctionMetrics, FileMetrics } from '../types';

export interface ParseResult {
  functions: FunctionMetrics[];
  metrics: FileMetrics;
  complexity: number;
}

export class JavaScriptParser {
  private content: string;
  private filePath: string;

  constructor(content: string, filePath: string) {
    this.content = content;
    this.filePath = filePath;
  }

  parse(): ParseResult {
    try {
      const ast = parser.parse(this.content, {
        sourceType: 'module',
        plugins: [
          'jsx',
          'typescript',
          'decorators-legacy',
          'classProperties',
          'objectRestSpread'
        ]
      });

      const functions: FunctionMetrics[] = [];
      let totalComplexity = 0;
      let maxComplexity = 0;

      // Traverse the AST
      traverse(ast, {
        FunctionDeclaration: (path) => {
          const metrics = this.analyzeFunction(path.node, path.node.loc);
          if (metrics) {
            functions.push(metrics);
            totalComplexity += metrics.complexity;
            maxComplexity = Math.max(maxComplexity, metrics.complexity);
          }
        },
        FunctionExpression: (path) => {
          const metrics = this.analyzeFunction(path.node, path.node.loc);
          if (metrics) {
            functions.push(metrics);
            totalComplexity += metrics.complexity;
            maxComplexity = Math.max(maxComplexity, metrics.complexity);
          }
        },
        ArrowFunctionExpression: (path) => {
          const metrics = this.analyzeFunction(path.node, path.node.loc);
          if (metrics) {
            functions.push(metrics);
            totalComplexity += metrics.complexity;
            maxComplexity = Math.max(maxComplexity, metrics.complexity);
          }
        },
        ClassMethod: (path) => {
          const metrics = this.analyzeFunction(path.node, path.node.loc);
          if (metrics) {
            functions.push(metrics);
            totalComplexity += metrics.complexity;
            maxComplexity = Math.max(maxComplexity, metrics.complexity);
          }
        },
        ObjectMethod: (path) => {
          const metrics = this.analyzeFunction(path.node, path.node.loc);
          if (metrics) {
            functions.push(metrics);
            totalComplexity += metrics.complexity;
            maxComplexity = Math.max(maxComplexity, metrics.complexity);
          }
        }
      });

      const linesOfCode = this.countLinesOfCode();
      const avgFunctionLength = functions.length > 0
        ? functions.reduce((sum, f) => sum + f.length, 0) / functions.length
        : 0;

      const metrics: FileMetrics = {
        complexity: functions.length > 0 ? totalComplexity / functions.length : 0,
        maxComplexity,
        duplication: 0, // Will be calculated separately
        maintainability: 0, // Will be calculated separately
        linesOfCode,
        functionCount: functions.length,
        averageFunctionLength: avgFunctionLength
      };

      return {
        functions,
        metrics,
        complexity: totalComplexity
      };
    } catch (error) {
      // If parsing fails, return basic metrics
      const linesOfCode = this.content.split('\n').length;
      return {
        functions: [],
        metrics: {
          complexity: 0,
          maxComplexity: 0,
          duplication: 0,
          maintainability: 0,
          linesOfCode,
          functionCount: 0,
          averageFunctionLength: 0
        },
        complexity: 0
      };
    }
  }

  private analyzeFunction(
    node: t.Function | t.ClassMethod | t.ObjectMethod,
    loc: t.SourceLocation | null
  ): FunctionMetrics | null {
    if (!loc) return null;

    const name = this.getFunctionName(node);
    const line = loc.start.line;
    const complexity = this.calculateCyclomaticComplexity(node);
    const length = this.calculateFunctionLength(node, loc);
    const parameters = this.getParameterCount(node);
    const maintainability = this.calculateMaintainabilityIndex(complexity, length, parameters);

    return {
      name,
      line,
      complexity,
      length,
      parameters,
      maintainability
    };
  }

  private getFunctionName(node: any): string {
    if (node.id && node.id.name) {
      return node.id.name;
    }

    if (node.key && node.key.name) {
      return node.key.name;
    }

    return '<anonymous>';
  }

  private calculateCyclomaticComplexity(
    node: t.Function | t.ClassMethod | t.ObjectMethod
  ): number {
    let complexity = 1; // Base complexity

    const traverse = (node: t.Node) => {
      if (!node) return;

      // Decision points that increase complexity
      switch (node.type) {
        case 'IfStatement':
        case 'WhileStatement':
        case 'DoWhileStatement':
        case 'ForStatement':
        case 'ForInStatement':
        case 'ForOfStatement':
        case 'ConditionalExpression':
        case 'SwitchCase':
          complexity++;
          break;
        case 'CatchClause':
          complexity++;
          break;
        case 'LogicalExpression':
          if (node.operator === '&&' || node.operator === '||') {
            complexity++;
          }
          break;
      }

      // Traverse child nodes
      for (const key in node) {
        if (node.hasOwnProperty(key)) {
          const child = (node as any)[key];
          if (Array.isArray(child)) {
            child.forEach(c => {
              if (c && typeof c === 'object' && c.type) {
                traverse(c);
              }
            });
          } else if (child && typeof child === 'object' && child.type) {
            traverse(child);
          }
        }
      }
    };

    traverse(node);
    return complexity;
  }

  private calculateFunctionLength(
    node: t.Function | t.ClassMethod | t.ObjectMethod,
    loc: t.SourceLocation
  ): number {
    return loc.end.line - loc.start.line + 1;
  }

  private getParameterCount(node: t.Function | t.ClassMethod | t.ObjectMethod): number {
    if (node.params) {
      return node.params.length;
    }
    return 0;
  }

  private calculateMaintainabilityIndex(
    complexity: number,
    length: number,
    parameters: number
  ): number {
    // Simplified maintainability index (MI)
    // MI = max(0, (171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)) * 100 / 171)
    // We'll use a simplified version

    if (length === 0) return 100;

    const volume = length; // Simplified Halstead volume
    const cc = complexity;
    const loc = length;

    const mi = Math.max(0, 171 - 5.2 * Math.log(volume) - 0.23 * cc - 16.2 * Math.log(loc));
    return Math.round((mi / 171) * 100);
  }

  private countLinesOfCode(): number {
    const lines = this.content.split('\n');
    let codeLines = 0;

    for (const line of lines) {
      const trimmed = line.trim();
      // Skip empty lines and comments
      if (trimmed && !trimmed.startsWith('//') && !trimmed.startsWith('/*') && !trimmed.startsWith('*')) {
        codeLines++;
      }
    }

    return codeLines;
  }
}
