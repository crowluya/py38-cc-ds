"""Metrics collection for task performance."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from task_tracker.models import Task, TaskStatus
from task_tracker.database import Database, TaskRepository


class MetricsCollector:
    """
    Collect and calculate task performance metrics.

    Provides methods for calculating various performance metrics
    including completion rates, execution times, and productivity patterns.
    """

    def __init__(self, database: Database):
        """
        Initialize metrics collector.

        Args:
            database: Database connection instance
        """
        self.db = database
        self.task_repo = TaskRepository(database)

    def calculate_completion_rate(
        self, period: str = "all"
    ) -> Dict[str, float]:
        """
        Calculate task completion rate.

        Args:
            period: Time period ('day', 'week', 'month', 'all')

        Returns:
            Dictionary with completion rate metrics
        """
        all_tasks = self._get_tasks_in_period(period)

        if not all_tasks:
            return {
                "total": 0,
                "completed": 0,
                "completion_rate": 0.0,
                "period": period,
            }

        total = len(all_tasks)
        completed = len([t for t in all_tasks if t.status == TaskStatus.COMPLETED])

        return {
            "total": total,
            "completed": completed,
            "completion_rate": round((completed / total) * 100, 2) if total > 0 else 0.0,
            "period": period,
        }

    def calculate_execution_times(self, period: str = "all") -> Dict[str, Any]:
        """
        Calculate execution time statistics.

        Args:
            period: Time period ('day', 'week', 'month', 'all')

        Returns:
            Dictionary with execution time statistics
        """
        tasks = self._get_tasks_in_period(period)
        completed_tasks = [t for t in tasks if t.completed_at and t.started_at]

        if not completed_tasks:
            return {
                "period": period,
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
            }

        durations = []
        for task in completed_tasks:
            duration = (task.completed_at - task.started_at).total_seconds() / 60  # minutes
            durations.append(duration)

        durations.sort()

        return {
            "period": period,
            "count": len(durations),
            "mean_minutes": round(sum(durations) / len(durations), 2),
            "median_minutes": round(durations[len(durations) // 2], 2),
            "min_minutes": round(min(durations), 2),
            "max_minutes": round(max(durations), 2),
            "total_minutes": round(sum(durations), 2),
        }

    def calculate_productivity_metrics(
        self, period: str = "week"
    ) -> Dict[str, Any]:
        """
        Calculate productivity metrics.

        Args:
            period: Time period ('day', 'week', 'month', 'all')

        Returns:
            Dictionary with productivity metrics
        """
        tasks = self._get_tasks_in_period(period)

        # Group by day
        tasks_by_day = defaultdict(list)
        for task in tasks:
            day = task.created_at.date()
            tasks_by_day[day].append(task)

        # Calculate daily metrics
        daily_metrics = []
        for day, day_tasks in sorted(tasks_by_day.items()):
            daily_metrics.append({
                "date": day.isoformat(),
                "created": len(day_tasks),
                "completed": len([t for t in day_tasks if t.status == TaskStatus.COMPLETED]),
            })

        if not daily_metrics:
            return {
                "period": period,
                "avg_tasks_per_day": 0,
                "peak_day": None,
                "daily_breakdown": [],
            }

        avg_tasks = sum(m["created"] for m in daily_metrics) / len(daily_metrics)
        peak_day = max(daily_metrics, key=lambda x: x["created"])

        return {
            "period": period,
            "avg_tasks_per_day": round(avg_tasks, 2),
            "peak_day": peak_day,
            "daily_breakdown": daily_metrics,
        }

    def identify_bottlenecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Identify potential bottlenecks and overdue tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of tasks that may be bottlenecks
        """
        all_tasks = self.task_repo.get_all()
        bottlenecks = []

        for task in all_tasks:
            # In-progress tasks that are taking too long
            if task.status == TaskStatus.IN_PROGRESS and task.started_at:
                hours_since_start = (datetime.now() - task.started_at).total_seconds() / 3600
                if hours_since_start > 24:  # More than 24 hours
                    bottlenecks.append({
                        "id": task.id,
                        "title": task.title,
                        "type": "long_running",
                        "hours_in_progress": round(hours_since_start, 2),
                        "started_at": task.started_at.isoformat(),
                    })

            # Overdue tasks
            if task.estimated_time and task.actual_time > task.estimated_time:
                bottlenecks.append({
                    "id": task.id,
                    "title": task.title,
                    "type": "overdue",
                    "estimated_time": task.estimated_time,
                    "actual_time": task.actual_time,
                    "overdue_by": task.actual_time - task.estimated_time,
                })

            # Blocked tasks
            if task.status == TaskStatus.BLOCKED:
                bottlenecks.append({
                    "id": task.id,
                    "title": task.title,
                    "type": "blocked",
                    "created_at": task.created_at.isoformat(),
                })

        # Sort by severity and limit
        bottlenecks.sort(key=lambda x: x.get("hours_in_progress", 0) or x.get("overdue_by", 0), reverse=True)
        return bottlenecks[:limit]

    def calculate_task_distribution(self) -> Dict[str, Any]:
        """
        Calculate task distribution by various attributes.

        Returns:
            Dictionary with distribution metrics
        """
        all_tasks = self.task_repo.get_all()

        # By status
        by_status = defaultdict(int)
        for task in all_tasks:
            by_status[task.status.value] += 1

        # By priority
        by_priority = defaultdict(int)
        for task in all_tasks:
            by_priority[task.priority.value] += 1

        # By project
        by_project = defaultdict(int)
        for task in all_tasks:
            if task.project:
                by_project[task.project] += 1

        # By tag
        by_tag = defaultdict(int)
        for task in all_tasks:
            for tag in task.tags:
                by_tag[tag] += 1

        return {
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "by_project": dict(sorted(by_project.items(), key=lambda x: x[1], reverse=True)),
            "by_tag": dict(sorted(by_tag.items(), key=lambda x: x[1], reverse=True)[:20]),
        }

    def calculate_velocity_metrics(self, period: str = "week") -> Dict[str, Any]:
        """
        Calculate team velocity metrics.

        Args:
            period: Time period ('day', 'week', 'month', 'all')

        Returns:
            Dictionary with velocity metrics
        """
        tasks = self._get_tasks_in_period(period)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED and t.completed_at]

        if not completed_tasks:
            return {
                "period": period,
                "total_completed": 0,
                "total_time_minutes": 0,
                "velocity_per_day": 0,
            }

        total_time = sum(t.actual_time for t in completed_tasks if t.actual_time)

        # Calculate period in days
        now = datetime.now()
        if period == "day":
            period_days = 1
        elif period == "week":
            period_days = 7
        elif period == "month":
            period_days = 30
        else:
            # Calculate from actual data
            earliest = min(t.created_at for t in tasks)
            period_days = max(1, (now - earliest).days)

        return {
            "period": period,
            "total_completed": len(completed_tasks),
            "total_time_minutes": total_time,
            "avg_time_per_task": round(total_time / len(completed_tasks), 2) if completed_tasks else 0,
            "velocity_per_day": round(len(completed_tasks) / period_days, 2),
        }

    def get_all_metrics(self, period: str = "week") -> Dict[str, Any]:
        """
        Get all available metrics.

        Args:
            period: Time period for metrics

        Returns:
            Dictionary with all metrics
        """
        return {
            "completion_rate": self.calculate_completion_rate(period),
            "execution_times": self.calculate_execution_times(period),
            "productivity": self.calculate_productivity_metrics(period),
            "velocity": self.calculate_velocity_metrics(period),
            "distribution": self.calculate_task_distribution(),
            "bottlenecks": self.identify_bottlenecks(),
        }

    def _get_tasks_in_period(self, period: str) -> List[Task]:
        """
        Get tasks created within a time period.

        Args:
            period: Time period ('day', 'week', 'month', 'all')

        Returns:
            List of tasks in the period
        """
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
