import { DuplicationMatch } from '../types';

interface CodeBlock {
  file: string;
  startLine: number;
  endLine: number;
  tokens: string[];
  hash: string;
}

export class DuplicationAnalyzer {
  private blocks: CodeBlock[] = [];
  private threshold = 100; // Minimum number of tokens to consider for duplication

  analyze(files: Map<string, string>): DuplicationMatch[] {
    this.blocks = [];

    // Parse all files into code blocks
    for (const [filePath, content] of files.entries()) {
      const blocks = this.extractCodeBlocks(filePath, content);
      this.blocks.push(...blocks);
    }

    // Find duplicates
    const duplicates = this.findDuplicates();

    return duplicates;
  }

  private extractCodeBlocks(filePath: string, content: string): CodeBlock[] {
    const blocks: CodeBlock[] = [];
    const lines = content.split('\n');

    // Extract function/method blocks (simplified)
    const blockRegex = /function\s+\w+|=>\s*{|class\s+\w+|^\s*(async\s+)?\w+\s*\([^)]*\)\s*{/gm;
    let match;
    const blockStarts: number[] = [];

    while ((match = blockRegex.exec(content)) !== null) {
      blockStarts.push(match.index);
    }

    // Create sliding window blocks
    const windowSize = 6; // Number of lines per block
    for (let i = 0; i < lines.length; i += windowSize) {
      const startLine = i;
      const endLine = Math.min(i + windowSize, lines.length);
      const blockLines = lines.slice(startLine, endLine);

      const tokens = this.tokenize(blockLines.join('\n'));
      if (tokens.length >= 3) {
        blocks.push({
          file: filePath,
          startLine: startLine + 1,
          endLine: endLine,
          tokens,
          hash: this.hashTokens(tokens)
        });
      }
    }

    return blocks;
  }

  private tokenize(content: string): string[] {
    // Remove strings, comments, and normalize
    let normalized = content
      .replace(/\/\*[\s\S]*?\*\//g, '') // Remove multi-line comments
      .replace(/\/\/.*/g, '') // Remove single-line comments
      .replace(/(["'`])(?:(?!\1|\\).|\\.)*\1/g, '""') // Replace strings with placeholder
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();

    // Split into tokens (simplified)
    const tokens = normalized
      .replace(/([{}();,])/g, ' $1 ')
      .split(/\s+/)
      .filter(t => t.length > 0);

    return tokens;
  }

  private hashTokens(tokens: string[]): string {
    return tokens.join('|');
  }

  private findDuplicates(): DuplicationMatch[] {
    const duplicates: DuplicationMatch[] = [];
    const hashMap = new Map<string, CodeBlock[]>();

    // Group blocks by hash
    for (const block of this.blocks) {
      if (!hashMap.has(block.hash)) {
        hashMap.set(block.hash, []);
      }
      hashMap.get(block.hash)!.push(block);
    }

    // Find duplicates (blocks with same hash in different files or locations)
    for (const [hash, blocks] of hashMap.entries()) {
      if (blocks.length >= 2) {
        // Calculate duplication percentage
        const uniqueFiles = new Set(blocks.map(b => b.file)).size;
        const totalBlocks = blocks.length;

        if (uniqueFiles >= 2 || (uniqueFiles === 1 && totalBlocks >= 2)) {
          const match: DuplicationMatch = {
            files: blocks.map(b => b.file),
            lines: blocks.map(b => [b.startLine, b.endLine]),
            tokens: blocks[0].tokens.length,
            duplicationPercentage: Math.min(100, (totalBlocks / this.blocks.length) * 100)
          };
          duplicates.push(match);
        }
      }
    }

    // Sort by duplication percentage (descending)
    return duplicates.sort((a, b) => b.duplicationPercentage - a.duplicationPercentage);
  }

  calculateFileDuplication(filePath: string, duplicates: DuplicationMatch[]): number {
    let totalDuplicateLines = 0;

    for (const duplicate of duplicates) {
      if (duplicate.files.includes(filePath)) {
        const fileIndex = duplicate.files.indexOf(filePath);
        const [start, end] = duplicate.lines[fileIndex];
        totalDuplicateLines += (end - start + 1);
      }
    }

    return totalDuplicateLines;
  }
}
