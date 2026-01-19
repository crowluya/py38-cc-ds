import { Database, Suggestion, FileActivity, TimeEntry } from '../types';
import { ProjectMatcher } from './projectMatcher';
import dayjs from 'dayjs';

export class SuggestionEngine {
  private recentActivities: FileActivity[] = [];
  private activityWeights: Map<string, number> = new Map();

  constructor(
    private db: Database,
    private matcher: ProjectMatcher,
    private confidenceThreshold: number = 0.5
  ) {}

  async generateSuggestions(limit: number = 5): Promise<Suggestion[]> {
    // Get recent activities (last hour)
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    this.recentActivities = await this.db.getRecentActivities(100);
    const recentActivities = this.recentActivities.filter((a) => a.timestamp >= oneHourAgo);

    if (recentActivities.length === 0) {
      return this.getFallbackSuggestions();
    }

    // Analyze activity patterns
    const projectScores = await this.calculateProjectScores(recentActivities);
    const taskScores = await this.calculateTaskScores(recentActivities);

    // Generate suggestions based on scores
    const suggestions: Suggestion[] = [];

    for (const [project, score] of projectScores.entries()) {
      if (score >= this.confidenceThreshold) {
        const confidence = Math.min(score, 1);
        const tasks = taskScores.get(project);

        suggestions.push({
          project,
          task: tasks && tasks.size > 0 ? this.getTopTask(tasks) : undefined,
          confidence,
          reason: this.generateReason(project, recentActivities),
        });
      }
    }

    // Sort by confidence and limit
    return suggestions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, limit);
  }

  async suggestForCurrentDirectory(): Promise<Suggestion | null> {
    const currentDir = process.cwd();

    const matchResult = await this.matcher.matchFromDirectory(currentDir);

    if (matchResult && matchResult.confidence >= this.confidenceThreshold) {
      return {
        project: matchResult.project,
        confidence: matchResult.confidence,
        reason: `Based on current directory: ${currentDir}`,
      };
    }

    return null;
  }

  private async calculateProjectScores(activities: FileActivity[]): Promise<Map<string, number>> {
    const scores = new Map<string, number>();
    const timeWeights = this.calculateTimeWeights(activities);

    for (const activity of activities) {
      if (!activity.project_suggestion) continue;

      const currentScore = scores.get(activity.project_suggestion) || 0;
      const timeWeight = timeWeights.get(activity.id) || 1;

      // More recent activities have higher weight
      scores.set(activity.project_suggestion, currentScore + timeWeight);
    }

    // Normalize scores to 0-1 range
    return this.normalizeScores(scores);
  }

  private async calculateTaskScores(activities: FileActivity[]): Promise<Map<string, Map<string, number>>> {
    const projectTaskScores = new Map<string, Map<string, number>>();

    for (const activity of activities) {
      if (!activity.project_suggestion || !activity.task_suggestion) continue;

      if (!projectTaskScores.has(activity.project_suggestion)) {
        projectTaskScores.set(activity.project_suggestion, new Map());
      }

      const taskScores = projectTaskScores.get(activity.project_suggestion)!;
      const currentScore = taskScores.get(activity.task_suggestion) || 0;
      taskScores.set(activity.task_suggestion, currentScore + 1);
    }

    return projectTaskScores;
  }

  private calculateTimeWeights(activities: FileActivity[]): Map<string, number> {
    const weights = new Map<string, number>();
    const now = Date.now();

    for (const activity of activities) {
      const age = now - activity.timestamp;
      // More recent activities have higher weight (exponential decay)
      const weight = Math.exp(-age / (30 * 60 * 1000)); // 30-minute half-life
      weights.set(activity.id, weight);
    }

    return weights;
  }

  private normalizeScores(scores: Map<string, number>): Map<string, number> {
    const maxScore = Math.max(...scores.values(), 1);
    const normalized = new Map<string, number>();

    for (const [key, value] of scores.entries()) {
      normalized.set(key, value / maxScore);
    }

    return normalized;
  }

  private getTopTask(taskScores: Map<string, number>): string {
    let topTask = '';
    let topScore = 0;

    for (const [task, score] of taskScores.entries()) {
      if (score > topScore) {
        topTask = task;
        topScore = score;
      }
    }

    return topTask;
  }

  private generateReason(project: string, activities: FileActivity[]): string {
    const projectActivities = activities.filter((a) => a.project_suggestion === project);
    const fileCount = new Set(projectActivities.map((a) => a.file_path)).size;

    if (fileCount === 1) {
      return `Working on ${fileCount} file in this project`;
    } else {
      return `Working on ${fileCount} files in this project`;
    }
  }

  private async getFallbackSuggestions(): Promise<Suggestion[]> {
    // Get the most recent time entry
    const entries = await this.db.listTimeEntries();
    const recentEntry = entries[0];

    if (recentEntry) {
      return [
        {
          project: recentEntry.project,
          task: recentEntry.task,
          confidence: 0.4,
          reason: 'Continuing previous work',
        },
      ];
    }

    // Get default project from config
    const projects = await this.db.listProjects();
    if (projects.length > 0) {
      return [
        {
          project: projects[0].name,
          confidence: 0.3,
          reason: 'No recent activity, suggesting first project',
        },
      ];
    }

    return [];
  }

  async learnFromUserFeedback(suggestion: Suggestion, accepted: boolean): Promise<void> {
    // Simple learning: boost confidence for accepted suggestions
    if (accepted) {
      // In a full implementation, this would update a learning model
      console.log(`✓ Learned: "${suggestion.project}" was accepted`);
    } else {
      console.log(`✗ Learned: "${suggestion.project}" was rejected`);
    }
  }
}
