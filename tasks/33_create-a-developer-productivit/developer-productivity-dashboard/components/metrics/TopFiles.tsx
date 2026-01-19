'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TopFilesProps {
  data: {
    file: string;
    commits: number;
    linesChanged: number;
  }[];
}

export function TopFiles({ data }: TopFilesProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Most Changed Files</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.map((file, index) => (
            <div key={file.file} className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-600 font-semibold text-sm flex-shrink-0">
                  {index + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm truncate" title={file.file}>
                    {file.file}
                  </p>
                  <p className="text-xs text-gray-600">
                    {file.commits} commits
                  </p>
                </div>
              </div>
              <div className="text-right flex-shrink-0 ml-2">
                <p className="text-sm font-medium">{file.linesChanged.toLocaleString()}</p>
                <p className="text-xs text-gray-600">lines</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
