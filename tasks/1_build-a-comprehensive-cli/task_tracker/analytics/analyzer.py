"""Task analyzer for advanced analytics."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import statistics

from task_tracker.models import Task, TaskStatus
from task_tracker.database import Database, TaskRepository


class TaskAnalyzer:
    """
    Advanced analysis of task performance patterns.

    Provides statistical analysis, pattern detection, and
    actionable insights from task data.
    """

    def __init__(self, database: Database):
        """
        Initialize task analyzer.

        Args:
            database: Database connection instance
        """
        self.db = database
        self.task_repo = TaskRepository(database)

    def analyze_peak_productivity_hours(self) -> Dict[str, Any]:
        """
        Analyze peak productivity hours based on task completion times.

        Returns:
            Dictionary with hourly productivity analysis
        """
        all_tasks = self.task_repo.get_all()
        completed_tasks = [t for t in all_tasks if t.completed_at]

        if not completed_tasks:
            return {"peak_hours": [], "analysis": "Insufficient data"}

        # Count completions by hour
        hour_counts = Counter(t.completed_at.hour for t in completed_tasks)

        # Find top 3 peak hours
        peak_hours = hour_counts.most_common(3)

        return {
            "peak_hours": [
                {"hour": h, "count": c, "time_range": f"{h}:00-{h+1}:00"}
                for h, c in peak_hours
            ],
            "total_completed": len(completed_tasks),
            "hourly_distribution": {
                hour: count for hour, count in sorted(hour_counts.items())
            },
        }

    def analyze_day_of_week_patterns(self) -> Dict[str, Any]:
        """
        Analyze task patterns by day of week.

        Returns:
            Dictionary with day-of-week analysis
        """
        all_tasks = self.task_repo.get_all()

        # Task creation by day
        creation_days = [t.created_at.strftime("%A") for t in all_tasks]
        creation_counts = Counter(creation_days)

        # Task completion by day
        completed_tasks = [t for t in all_tasks if t.completed_at]
        completion_days = [t.completed_at.strftime("%A") for t in completed_tasks]
        completion_counts = Counter(completion_days)

        # Order by weekday
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return {
            "creation_by_day": {day: creation_counts.get(day, 0) for day in weekday_order},
            "completion_by_day": {day: completion_counts.get(day, 0) for day in weekday_order},
            "most_productive_day": completion_counts.most_common(1)[0] if completion_counts else None,
            "total_analyzed": len(all_tasks),
        }

    def analyze_task_type_correlations(self) -> Dict[str, Any]:
        """
        Analyze correlations between task attributes and outcomes.

        Returns:
            Dictionary with correlation analysis
        """
        all_tasks = self.task_repo.get_all()

        # Completion rate by priority
        priority_stats = {}
        for priority in ["low", "medium", "high", "critical"]:
            priority_tasks = [t for t in all_tasks if t.priority.value == priority]
            if priority_tasks:
                completed = [t for t in priority_tasks if t.status == TaskStatus.COMPLETED]
                priority_stats[priority] = {
                    "total": len(priority_tasks),
                    "completed": len(completed),
                    "completion_rate": round(len(completed) / len(priority_tasks) * 100, 2),
                }

        # Completion rate by project
        project_stats = {}
        project_tasks = {}
        for task in all_tasks:
            if task.project:
                if task.project not in project_tasks:
                    project_tasks[task.project] = []
                project_tasks[task.project].append(task)

        for project, tasks in project_tasks.items():
            completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            project_stats[project] = {
                "total": len(tasks),
                "completed": len(completed),
                "completion_rate": round(len(completed) / len(tasks) * 100, 2),
            }

        return {
            "by_priority": priority_stats,
            "by_project": dict(sorted(project_stats.items(), key=lambda x: x[1]["completion_rate"], reverse=True)[:10]),
        }

    def calculate_efficiency_score(self) -> Dict[str, Any]:
        """
        Calculate overall efficiency score.

        Returns:
            Dictionary with efficiency metrics
        """
        all_tasks = self.task_repo.get_all()
        completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]

        if not completed_tasks:
            return {"efficiency_score": 0, "insufficient_data": True}

        # On-time completion rate
        on_time = []
        for task in completed_tasks:
            if task.estimated_time and task.actual_time <= task.estimated_time:
                on_time.append(task)
            elif not task.estimated_time:
                on_time.append(task)  # No estimate, count as on-time

        on_time_rate = len(on_time) / len(completed_tasks) if completed_tasks else 0

        # Completion rate
        completion_rate = len(completed_tasks) / len(all_tasks) if all_tasks else 0

        # Average execution time vs estimated
        accurate_estimates = 0
        for task in completed_tasks:
            if task.estimated_time:
                variance = abs(task.actual_time - task.estimated_time) / task.estimated_time
                if variance <= 0.2:  # Within 20%
                    accurate_estimates += 1

        estimate_accuracy = accurate_estimates / len(completed_tasks) if completed_tasks else 0

        # Overall efficiency score (weighted average)
        efficiency_score = (
            on_time_rate * 0.4 +
            completion_rate * 0.4 +
            estimate_accuracy * 0.2
        ) * 100

        return {
            "efficiency_score": round(efficiency_score, 2),
            "on_time_completion_rate": round(on_time_rate * 100, 2),
            "overall_completion_rate": round(completion_rate * 100, 2),
            "estimate_accuracy": round(estimate_accuracy * 100, 2),
            "total_tasks": len(all_tasks),
            "completed_tasks": len(completed_tasks),
        }

    def generate_insights(self) -> List[Dict[str, Any]]:
        """
        Generate actionable insights from task data.

        Returns:
            List of insights with recommendations
        """
        insights = []
        all_tasks = self.task_repo.get_all()
        completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]

        # Insight 1: Completion trend
        if len(all_tasks) > 10:
            recent = [t for t in all_tasks if (datetime.now() - t.created_at).days <= 7]
            if recent:
                completion_rate = len([t for t in recent if t.status == TaskStatus.COMPLETED]) / len(recent) * 100
                if completion_rate > 80:
                    insights.append({
                        "type": "positive",
                        "title": "High Completion Rate",
                        "message": f"Recent completion rate is {completion_rate:.1f}%",
                        "recommendation": "Continue current productivity practices.",
                    })
                elif completion_rate < 50:
                    insights.append({
                        "type": "warning",
                        "title": "Low Completion Rate",
                        "message": f"Recent completion rate is {completion_rate:.1f}%",
                        "recommendation": "Consider reducing work-in-progress and focusing on completing existing tasks.",
                    })

        # Insight 2: Estimate accuracy
        tasks_with_estimates = [t for t in completed_tasks if t.estimated_time]
        if tasks_with_estimates:
            overestimated = [t for t in tasks_with_estimates if t.actual_time < t.estimated_time]
            underestimated = [t for t in tasks_with_estimates if t.actual_time > t.estimated_time]

            if len(underestimated) > len(overestimated):
                insights.append({
                    "type": "warning",
                    "title": "Consistent Underestimation",
                    "message": f"{len(underestimated)} tasks took longer than estimated",
                    "recommendation": "Consider adding buffer time to estimates or breaking down large tasks.",
                })

        # Insight 3: Stalled tasks
        stalled = [
            t for t in all_tasks
            if t.status == TaskStatus.IN_PROGRESS and
            (datetime.now() - t.updated_at).days > 3
        ]
        if stalled:
            insights.append({
                "type": "warning",
                "title": "Stalled Tasks Detected",
                "message": f"{len(stalled)} tasks haven't been updated in 3+ days",
                "recommendation": "Review and update status of stalled tasks, or consider breaking them into smaller subtasks.",
            })

        # Insight 4: Priority balance
        high_priority_incomplete = [
            t for t in all_tasks
            if t.priority.value in ["high", "critical"] and
            t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ]
        if len(high_priority_incomplete) > 5:
            insights.append({
                "type": "warning",
                "title": "High Priority Backlog",
                "message": f"{len(high_priority_incomplete)} high/critical priority tasks pending",
                "recommendation": "Focus on completing high-priority tasks before taking on new work.",
            })

        return insights

    def compare_periods(
        self, period1: str, period2: str
    ) -> Dict[str, Any]:
        """
        Compare metrics between two time periods.

        Args:
            period1: First period ('day', 'week', 'month')
            period2: Second period ('day', 'week', 'month')

        Returns:
            Dictionary with comparison metrics
        """
        # Get tasks for each period
        tasks1 = self._get_tasks_in_period(period1)
        tasks2 = self._get_tasks_in_period(period2)

        completed1 = len([t for t in tasks1 if t.status == TaskStatus.COMPLETED])
        completed2 = len([t for t in tasks2 if t.status == TaskStatus.COMPLETED])

        return {
            "period1": {
                "name": period1,
                "total": len(tasks1),
                "completed": completed1,
                "completion_rate": round(completed1 / len(tasks1) * 100, 2) if tasks1 else 0,
            },
            "period2": {
                "name": period2,
                "total": len(tasks2),
                "completed": completed2,
                "completion_rate": round(completed2 / len(tasks2) * 100, 2) if tasks2 else 0,
            },
            "change": {
                "total_tasks": len(tasks2) - len(tasks1),
                "completed": completed2 - completed1,
            },
        }

    def _get_tasks_in_period(self, period: str) -> List[Task]:
        """Get tasks created within a time period."""
        all_tasks = self.task_repo.get_all()

        if period == "all":
            return all_tasks

        now = datetime.now()
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            return all_tasks

        return [t for t in all_tasks if t.created_at >= cutoff]
