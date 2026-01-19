import { NextRequest, NextResponse } from 'next/server';
import { GitScanner } from '@/lib/git/scanner';
import { GitLogParser } from '@/lib/git/parser';
import { calculateMetrics } from '@/lib/git/metrics';
import { AnalysisOptions } from '@/lib/git/types';

export async function POST(request: NextRequest) {
  try {
    const { repoPath, options } = await request.json();

    if (!repoPath) {
      return NextResponse.json(
        { error: 'Repository path is required' },
        { status: 400 }
      );
    }

    // Validate repository
    const isValid = await GitScanner.validateRepository(repoPath);
    if (!isValid) {
      return NextResponse.json(
        { error: 'Invalid Git repository' },
        { status: 400 }
      );
    }

    // Get repository info
    const scanner = new GitScanner(repoPath);
    const repoInfo = await scanner.getRepositoryInfo();

    // Parse commits
    const parser = new GitLogParser(repoPath);
    const commits = await parser.parseCommits(options);

    if (commits.length === 0) {
      return NextResponse.json(
        { error: 'No commits found in repository' },
        { status: 400 }
      );
    }

    // Calculate metrics
    const metrics = calculateMetrics(commits);

    return NextResponse.json({
      repository: repoInfo,
      metrics,
    });
  } catch (error) {
    console.error('Analysis error:', error);
    return NextResponse.json(
      { error: 'Failed to analyze repository' },
      { status: 500 }
    );
  }
}
