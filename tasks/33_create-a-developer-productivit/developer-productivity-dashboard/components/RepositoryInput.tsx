'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { FolderOpen, Loader2 } from 'lucide-react';

interface RepositoryInputProps {
  onAnalyze: (path: string) => void;
  isLoading: boolean;
}

export function RepositoryInput({ onAnalyze, isLoading }: RepositoryInputProps) {
  const [repoPath, setRepoPath] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoPath.trim()) {
      onAnalyze(repoPath.trim());
    }
  };

  const handleBrowse = async () => {
    // In a real desktop app, this would open a folder picker
    // For web, we'll just focus the input
    document.getElementById('repo-path')?.focus();
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FolderOpen className="w-6 h-6" />
          Analyze Repository
        </CardTitle>
        <CardDescription>
          Enter the path to a local Git repository to analyze its metrics
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex gap-2">
            <Input
              id="repo-path"
              type="text"
              placeholder="/path/to/your/repository"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleBrowse}
              disabled={isLoading}
            >
              Browse
            </Button>
          </div>
          <Button
            type="submit"
            className="w-full"
            disabled={isLoading || !repoPath.trim()}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Repository'
            )}
          </Button>
        </form>
        <div className="mt-4 text-sm text-gray-600">
          <p className="font-semibold mb-2">Example paths:</p>
          <ul className="space-y-1 text-xs">
            <li className="text-gray-500">• /home/user/projects/my-app</li>
            <li className="text-gray-500">• C:\Users\user\projects\my-app</li>
            <li className="text-gray-500">• ~/projects/opensource/repo</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
