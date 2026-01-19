'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TopContributorsProps {
  data: {
    author: string;
    commits: number;
    linesChanged: number;
  }[];
}

export function TopContributors({ data }: TopContributorsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Contributors</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.map((contributor, index) => (
            <div key={contributor.author} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600 font-semibold text-sm">
                  {index + 1}
                </div>
                <div>
                  <p className="font-medium text-sm">{contributor.author}</p>
                  <p className="text-xs text-gray-600">
                    {contributor.commits} commits
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{contributor.linesChanged.toLocaleString()}</p>
                <p className="text-xs text-gray-600">lines changed</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
