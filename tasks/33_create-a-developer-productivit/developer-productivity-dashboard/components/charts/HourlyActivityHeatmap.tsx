'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface HourlyActivityHeatmapProps {
  data: {
    hour: number;
    day: number;
    count: number;
  }[];
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export function HourlyActivityHeatmap({ data }: HourlyActivityHeatmapProps) {
  // Find max count for color scaling
  const maxCount = Math.max(...data.map(d => d.count), 1);

  // Get color intensity based on count
  const getColor = (count: number) => {
    if (count === 0) return 'bg-gray-100';
    const intensity = count / maxCount;
    if (intensity < 0.25) return 'bg-blue-100';
    if (intensity < 0.5) return 'bg-blue-200';
    if (intensity < 0.75) return 'bg-blue-300';
    return 'bg-blue-500';
  };

  // Create a map for quick lookup
  const activityMap = new Map(data.map(d => [`${d.day}-${d.hour}`, d.count]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hourly Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex text-xs text-gray-600 mb-2">
            <div className="w-12"></div>
            {Array.from({ length: 24 }, (_, i) => (
              <div key={i} className="flex-1 text-center">
                {i % 6 === 0 ? i : ''}
              </div>
            ))}
          </div>
          {DAYS.map((day, dayIndex) => (
            <div key={day} className="flex items-center">
              <div className="w-12 text-xs text-gray-600">{day}</div>
              {Array.from({ length: 24 }, (_, hour) => {
                const count = activityMap.get(`${dayIndex}-${hour}`) || 0;
                const colorClass = getColor(count);
                return (
                  <div
                    key={hour}
                    className={`flex-1 aspect-square ${colorClass} rounded-sm`}
                    title={`${day} ${hour}:00 - ${count} commits`}
                  />
                );
              })}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-end gap-2 mt-4 text-xs text-gray-600">
          <span>Less</span>
          <div className="flex gap-1">
            <div className="w-4 h-4 bg-gray-100 rounded-sm"></div>
            <div className="w-4 h-4 bg-blue-100 rounded-sm"></div>
            <div className="w-4 h-4 bg-blue-200 rounded-sm"></div>
            <div className="w-4 h-4 bg-blue-300 rounded-sm"></div>
            <div className="w-4 h-4 bg-blue-500 rounded-sm"></div>
          </div>
          <span>More</span>
        </div>
      </CardContent>
    </Card>
  );
}
