import { NextRequest, NextResponse } from 'next/server';
import { GitScanner } from '@/lib/git/scanner';

export async function POST(request: NextRequest) {
  try {
    const { repoPath } = await request.json();

    if (!repoPath) {
      return NextResponse.json(
        { error: 'Repository path is required' },
        { status: 400 }
      );
    }

    const isValid = await GitScanner.validateRepository(repoPath);

    if (!isValid) {
      return NextResponse.json(
        { error: 'Invalid Git repository' },
        { status: 400 }
      );
    }

    const scanner = new GitScanner(repoPath);
    const repoInfo = await scanner.getRepositoryInfo();
    const branches = await scanner.getBranches();
    const authors = await scanner.getAuthors();

    return NextResponse.json({
      valid: true,
      repository: repoInfo,
      branches,
      authors,
    });
  } catch (error) {
    console.error('Validation error:', error);
    return NextResponse.json(
      { error: 'Failed to validate repository' },
      { status: 500 }
    );
  }
}
