import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

export interface FileDiscoveryOptions {
  extensions: string[];
  ignore: string[];
  rootPath: string;
}

export class FileDiscoverer {
  private options: FileDiscoveryOptions;

  constructor(options: FileDiscoveryOptions) {
    this.options = options;
  }

  async discoverFiles(): Promise<string[]> {
    const { extensions, ignore, rootPath } = this.options;

    // Build glob pattern for included files
    const patterns = extensions.map(ext => `**/*${ext}`);

    // Discover all matching files
    const files = await glob(patterns, {
      cwd: rootPath,
      absolute: true,
      ignore: this.buildIgnorePatterns(ignore, rootPath),
      nodir: true
    });

    return files.sort();
  }

  private buildIgnorePatterns(ignore: string[], rootPath: string): string[] {
    const ignorePatterns: string[] = [];

    // Add user-specified ignore patterns
    for (const pattern of ignore) {
      // Convert relative patterns to be relative to rootPath
      if (!path.isAbsolute(pattern)) {
        ignorePatterns.push(pattern);
      } else {
        // For absolute patterns, make them relative to cwd
        ignorePatterns.push(path.relative(rootPath, pattern));
      }
    }

    return ignorePatterns;
  }

  static getFileLanguage(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();

    const languageMap: { [key: string]: string } = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.mjs': 'javascript',
      '.cjs': 'javascript',
      '.py': 'python',
      '.java': 'java',
      '.cpp': 'cpp',
      '.c': 'c',
      '.cs': 'csharp',
      '.go': 'go',
      '.rs': 'rust',
      '.rb': 'ruby',
      '.php': 'php'
    };

    return languageMap[ext] || 'unknown';
  }

  static getFileStats(filePath: string): { lines: number; size: number } {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n').length;
      const size = Buffer.byteLength(content, 'utf-8');

      return { lines, size };
    } catch (error) {
      return { lines: 0, size: 0 };
    }
  }

  static async readFileContent(filePath: string): Promise<string> {
    try {
      return await fs.promises.readFile(filePath, 'utf-8');
    } catch (error) {
      throw new Error(`Failed to read file: ${filePath}`);
    }
  }
}
