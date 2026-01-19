import { AnalysisResult } from '../types';

export class JsonReporter {
  generateReport(result: AnalysisResult): string {
    const report = {
      summary: result.summary,
      suggestions: result.suggestions,
      files: result.files.map(file => ({
        path: file.path,
        language: file.language,
        metrics: file.metrics,
        issues: file.issues,
        functions: file.functions
      })),
      config: result.config,
      generatedAt: new Date().toISOString()
    };

    return JSON.stringify(report, null, 2);
  }
}
