"""Trend analysis for task performance over time."""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

from task_tracker.models import Task, TaskStatus
from task_tracker.database import Database, TaskRepository


class TrendAnalyzer:
    """
    Analyze trends in task performance over time.

    Provides time-series analysis, moving averages, and
    trend detection for productivity metrics.
    """

    def __init__(self, database: Database):
        """
        Initialize trend analyzer.

        Args:
            database: Database connection instance
        """
        self.db = database
        self.task_repo = TaskRepository(database)

    def calculate_completion_trend(
        self, days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate task completion trend over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with completion trend data
        """
        all_tasks = self.task_repo.get_all()
        cutoff = datetime.now() - timedelta(days=days)

        # Filter tasks within period
        recent_tasks = [t for t in all_tasks if t.completed_at and t.completed_at >= cutoff]

        # Group by day
        daily_completions = defaultdict(int)
        for task in recent_tasks:
            day = task.completed_at.date()
            daily_completions[day] += 1

        # Calculate moving average
        if len(daily_completions) >= 7:
            moving_avg = self._calculate_moving_average(daily_completions, window=7)
        else:
            moving_avg = {}

        # Determine trend direction
        if len(daily_completions) >= 2:
            sorted_days = sorted(daily_completions.keys())
            recent_avg = sum(daily_completions[d] for d in sorted_days[-7:]) / min(7, len(sorted_days))
            earlier_avg = sum(daily_completions[d] for d in sorted_days[:-7]) / max(1, len(sorted_days) - 7)

            if recent_avg > earlier_avg * 1.1:
                trend = "increasing"
            elif recent_avg < earlier_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "period_days": days,
            "total_completed": len(recent_tasks),
            "daily_completions": {str(k): v for k, v in sorted(daily_completions.items())},
            "moving_average": {str(k): v for k, v in sorted(moving_avg.items())},
            "trend": trend,
            "avg_per_day": round(sum(daily_completions.values()) / len(daily_completions), 2) if daily_completions else 0,
        }

    def calculate_velocity_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate velocity trend (tasks completed per day).

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with velocity trend data
        """
        all_tasks = self.task_repo.get_all()
        cutoff = datetime.now() - timedelta(days=days)

        completed_tasks = [t for t in all_tasks if t.completed_at and t.completed_at >= cutoff]

        # Calculate cumulative completions
        daily_velocity = defaultdict(int)
        for task in completed_tasks:
            day = task.completed_at.date()
            daily_velocity[day] += 1

        # Calculate 7-day rolling velocity
        rolling_velocity = {}
        sorted_days = sorted(daily_velocity.keys())

        for i, day in enumerate(sorted_days):
            start_idx = max(0, i - 6)
            week_days = sorted_days[start_idx:i+1]
            rolling_velocity[day] = sum(daily_velocity[d] for d in week_days)

        return {
            "period_days": days,
            "total_completed": len(completed_tasks),
            "daily_velocity": {str(k): v for k, v in sorted(daily_velocity.items())},
            "rolling_7day_velocity": {str(k): v for k, v in sorted(rolling_velocity.items())},
            "current_velocity": rolling_velocity[sorted_days[-1]] if rolling_velocity else 0,
        }

    def analyze_cycle_time_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze cycle time (time from start to completion) trend.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with cycle time trend
        """
        all_tasks = self.task_repo.get_all()
        cutoff = datetime.now() - timedelta(days=days)

        completed_tasks = [
            t for t in all_tasks
            if t.completed_at and t.started_at and t.completed_at >= cutoff
        ]

        cycle_times = []
        for task in completed_tasks:
            cycle_time = (task.completed_at - task.started_at).total_seconds() / 3600  # hours
            cycle_times.append({
                "date": task.completed_at.date(),
                "cycle_time_hours": round(cycle_time, 2),
            })

        if not cycle_times:
            return {
                "period_days": days,
                "total_analyzed": 0,
                "avg_cycle_time": 0,
                "trend": "insufficient_data",
            }

        # Calculate moving average
        daily_avg = defaultdict(list)
        for ct in cycle_times:
            daily_avg[ct["date"]].append(ct["cycle_time_hours"])

        daily_avg_cycle = {day: round(sum(times) / len(times), 2) for day, times in daily_avg.items()}

        # Determine trend
        sorted_days = sorted(daily_avg_cycle.keys())
        if len(sorted_days) >= 7:
            recent_avg = sum(daily_avg_cycle[d] for d in sorted_days[-7:]) / 7
            earlier_avg = sum(daily_avg_cycle[d] for d in sorted_days[:-7]) / (len(sorted_days) - 7)

            if recent_avg < earlier_avg * 0.9:
                trend = "improving"  # Cycle time decreasing
            elif recent_avg > earlier_avg * 1.1:
                trend = "degrading"  # Cycle time increasing
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "period_days": days,
            "total_analyzed": len(cycle_times),
            "avg_cycle_time_hours": round(sum(ct["cycle_time_hours"] for ct in cycle_times) / len(cycle_times), 2),
            "daily_average": {str(k): v for k, v in sorted(daily_avg_cycle.items())},
            "trend": trend,
        }

    def calculate_burndown(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate burndown chart data.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with burndown data
        """
        all_tasks = self.task_repo.get_all()
        cutoff = datetime.now() - timedelta(days=days)

        # Get tasks created and completed each day
        daily_created = defaultdict(int)
        daily_completed = defaultdict(int)

        for task in all_tasks:
            if task.created_at >= cutoff:
                daily_created[task.created_at.date()] += 1
            if task.completed_at and task.completed_at >= cutoff:
                daily_completed[task.completed_at.date()] += 1

        # Calculate cumulative counts
        all_days = sorted(set(daily_created.keys()) | set(daily_completed.keys()))

        burndown_data = []
        cumulative_open = len([t for t in all_tasks if t.created_at < cutoff and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]])

        for day in all_days:
            cumulative_open += daily_created[day]
            cumulative_open -= daily_completed[day]
            burndown_data.append({
                "date": str(day),
                "created": daily_created[day],
                "completed": daily_completed[day],
                "remaining": cumulative_open,
            })

        return {
            "period_days": days,
            "burndown_data": burndown_data,
            "start_remaining": burndown_data[0]["remaining"] if burndown_data else 0,
            "end_remaining": burndown_data[-1]["remaining"] if burndown_data else 0,
            "net_change": (burndown_data[-1]["remaining"] - burndown_data[0]["remaining"]) if burndown_data else 0,
        }

    def forecast_completion(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        Forecast task completion based on historical velocity.

        Args:
            days_ahead: Number of days to forecast

        Returns:
            Dictionary with forecast data
        """
        # Get recent velocity (last 30 days)
        velocity_trend = self.calculate_velocity_trend(days=30)
        current_velocity = velocity_trend.get("current_velocity", 0) / 7  # Per day

        # Get current pending tasks
        all_tasks = self.task_repo.get_all()
        pending = len([t for t in all_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]])

        if current_velocity == 0:
            return {
                "forecast_days": days_ahead,
                "current_pending": pending,
                "velocity_per_day": 0,
                "projected_completions": 0,
                "message": "No velocity data available for forecasting",
            }

        projected_completions = round(current_velocity * days_ahead)
        remaining_after = max(0, pending - projected_completions)

        return {
            "forecast_days": days_ahead,
            "current_pending": pending,
            "velocity_per_day": round(current_velocity, 2),
            "projected_completions": projected_completions,
            "projected_remaining": remaining_after,
            "clearance_days": round(pending / current_velocity, 1) if current_velocity > 0 else None,
        }

    def _calculate_moving_average(
        self, data: dict, window: int = 7
    ) -> Dict[str, float]:
        """
        Calculate moving average for time series data.

        Args:
            data: Dictionary with dates as keys, values as values
            window: Window size for moving average

        Returns:
            Dictionary with moving averages
        """
        sorted_items = sorted(data.items())
        moving_avg = {}

        for i, (date, value) in enumerate(sorted_items):
            start_idx = max(0, i - window + 1)
            window_items = sorted_items[start_idx:i+1]
            avg = sum(v for _, v in window_items) / len(window_items)
            moving_avg[date] = round(avg, 2)

        return moving_avg
