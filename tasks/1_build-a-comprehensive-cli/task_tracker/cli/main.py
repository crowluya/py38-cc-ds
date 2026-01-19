"""Main CLI interface for task tracker."""

import click
import sys
from pathlib import Path
from typing import Optional

from task_tracker.database import Database
from task_tracker.tracker import TaskTracker
from task_tracker.reporting import ReportGenerator


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """
    Task Performance Analytics CLI

    A comprehensive tool for monitoring and analyzing workspace
    task performance metrics.
    """
    # Initialize database and tracker
    ctx.ensure_object(dict)
    db = Database()
    ctx.obj["db"] = db
    ctx.obj["tracker"] = TaskTracker(db)
    ctx.obj["report_generator"] = ReportGenerator(db)


@cli.command()
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--description", "-d", default="", help="Task description")
@click.option("--priority", "-p", default="medium", type=click.Choice(["low", "medium", "high", "critical"]), help="Task priority")
@click.option("--tag", "tags", multiple=True, help="Task tags (can use multiple times)")
@click.option("--project", help="Project name")
@click.option("--estimate", type=int, help="Estimated time in minutes")
@click.option("--assignee", help="Task assignee")
@click.pass_context
def add(ctx, title, description, priority, tags, project, estimate, assignee):
    """Add a new task."""
    tracker = ctx.obj["tracker"]

    task = tracker.create_task(
        title=title,
        description=description,
        priority=priority,
        tags=list(tags) if tags else None,
        project=project,
        estimated_time=estimate,
        assignee=assignee,
    )

    click.echo(click.style(f"✓ Task created with ID: {task.id}", fg="green"))
    click.echo(f"  Title: {task.title}")
    click.echo(f"  Status: {task.status.value}")
    click.echo(f"  Priority: {task.priority.value}")


@cli.command()
@click.option("--status", "-s", type=click.Choice(["pending", "in_progress", "paused", "completed", "blocked", "cancelled"]), help="Filter by status")
@click.option("--project", "-p", help="Filter by project")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--search", help="Search in title and description")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def list(ctx, status, project, tag, search, format):
    """List tasks with optional filtering."""
    tracker = ctx.obj["tracker"]

    tasks = tracker.list_tasks(
        status=status,
        project=project,
        tag=tag,
        search=search,
    )

    if not tasks:
        click.echo("No tasks found.")
        return

    if format == "json":
        import json
        click.echo(json.dumps([t.to_dict() for t in tasks], indent=2, default=str))
    else:
        # Table format
        from tabulate import tabulate

        table_data = []
        for task in tasks:
            table_data.append([
                task.id,
                task.title[:40],
                task.status.value,
                task.priority.value,
                task.project or "-",
                task.created_at.strftime("%Y-%m-%d"),
            ])

        click.echo(tabulate(
            table_data,
            headers=["ID", "Title", "Status", "Priority", "Project", "Created"],
            tablefmt="grid",
        ))
        click.echo(f"\nTotal: {len(tasks)} tasks")


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def show(ctx, task_id):
    """Show task details."""
    tracker = ctx.obj["tracker"]

    task = tracker.get_task(task_id)
    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"Task #{task.id}", fg="blue", bold=True))
    click.echo(f"Title: {task.title}")
    click.echo(f"Description: {task.description or 'No description'}")
    click.echo(f"Status: {task.status.value}")
    click.echo(f"Priority: {task.priority.value}")
    click.echo(f"Project: {task.project or 'None'}")
    click.echo(f"Assignee: {task.assignee or 'None'}")
    click.echo(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}")
    if task.started_at:
        click.echo(f"Started: {task.started_at.strftime('%Y-%m-%d %H:%M')}")
    if task.completed_at:
        click.echo(f"Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"Estimated time: {task.estimated_time or 'N/A'} minutes")
    click.echo(f"Actual time: {task.actual_time} minutes")
    if task.tags:
        click.echo(f"Tags: {', '.join(task.tags)}")


@cli.command()
@click.argument("task_id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "critical"]), help="New priority")
@click.option("--tag", "tags", multiple=True, help="New tags (replaces existing)")
@click.option("--project", help="New project")
@click.option("--estimate", type=int, help="New estimated time in minutes")
@click.option("--assignee", help="New assignee")
@click.pass_context
def update(ctx, task_id, title, description, priority, tags, project, estimate, assignee):
    """Update task details."""
    tracker = ctx.obj["tracker"]

    task = tracker.update_task(
        task_id=task_id,
        title=title,
        description=description,
        priority=priority,
        tags=list(tags) if tags else None,
        project=project,
        estimated_time=estimate,
        assignee=assignee,
    )

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Task {task_id} updated", fg="green"))


@cli.command()
@click.argument("task_id", type=int)
@click.option("--actual-time", type=int, help="Actual time spent in minutes")
@click.pass_context
def complete(ctx, task_id, actual_time):
    """Mark task as completed."""
    tracker = ctx.obj["tracker"]

    task = tracker.complete_task(task_id, actual_time=actual_time)

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Task {task_id} marked as completed", fg="green"))


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def start(ctx, task_id):
    """Start working on a task."""
    tracker = ctx.obj["tracker"]

    task = tracker.start_task(task_id)

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Task {task_id} started", fg="green"))


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def pause(ctx, task_id):
    """Pause work on a task."""
    tracker = ctx.obj["tracker"]

    task = tracker.pause_task(task_id)

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Task {task_id} paused", fg="yellow"))


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def delete(ctx, task_id):
    """Delete a task."""
    tracker = ctx.obj["tracker"]

    if click.confirm(f"Are you sure you want to delete task {task_id}?"):
        success = tracker.delete_task(task_id)

        if success:
            click.echo(click.style(f"✓ Task {task_id} deleted", fg="green"))
        else:
            click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
            sys.exit(1)


@cli.command()
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "all"]), default="week", help="Time period")
@click.option("--type", "-t", type=click.Choice(["summary", "detailed", "trend", "insights"]), default="summary", help="Report type")
@click.option("--output", "-o", help="Save report to file")
@click.pass_context
def report(ctx, period, type, output):
    """Generate performance report."""
    report_gen = ctx.obj["report_generator"]

    if type == "summary":
        report_text = report_gen.generate_summary_report(period)
    elif type == "detailed":
        report_text = report_gen.generate_detailed_report(period)
    elif type == "trend":
        report_text = report_gen.generate_trend_report()
    else:  # insights
        report_text = report_gen.generate_insights_report()

    if output:
        with open(output, "w") as f:
            f.write(report_text)
        click.echo(click.style(f"✓ Report saved to {output}", fg="green"))
    else:
        click.echo(report_text)


@cli.command()
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "all"]), default="week", help="Time period")
@click.pass_context
def analytics(ctx, period):
    """Show task analytics."""
    tracker = ctx.obj["tracker"]

    stats = tracker.get_statistics()

    click.echo(click.style("TASK ANALYTICS", fg="blue", bold=True))
    click.echo("=" * 50)
    click.echo(f"Total Tasks: {stats['total']}")
    click.echo(f"\nBy Status:")
    for status, count in stats["by_status"].items():
        click.echo(f"  {status}: {count}")
    click.echo(f"\nBy Priority:")
    for priority, count in stats["by_priority"].items():
        click.echo(f"  {priority}: {count}")
    click.echo(f"\nAvg Completion Time: {stats['avg_completion_time_minutes']} minutes")


@cli.command()
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "all"]), default="week", help="Time period")
@click.pass_context
def trends(ctx, period):
    """Show productivity trends."""
    report_gen = ctx.obj["report_generator"]

    report_text = report_gen.generate_trend_report()
    click.echo(report_text)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--duration", type=int, required=True, help="Duration in minutes")
@click.option("--notes", help="Optional notes")
@click.pass_context
def log_time(ctx, task_id, duration, notes):
    """Log time spent on a task."""
    tracker = ctx.obj["tracker"]

    task = tracker.add_time_entry(task_id, duration, notes)

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Logged {duration} minutes for task {task_id}", fg="green"))


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def history(ctx, task_id):
    """Show task history."""
    tracker = ctx.obj["tracker"]

    events = tracker.get_task_history(task_id)

    if not events:
        click.echo(f"No history found for task {task_id}")
        return

    click.echo(click.style(f"Task #{task_id} History", fg="blue", bold=True))
    click.echo("=" * 50)

    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        click.echo(f"{timestamp} - {event.event_type.value}")
        if event.new_value:
            click.echo(f"  → {event.new_value}")


@cli.command()
@click.option("--output", "-o", required=True, help="Output file path")
@click.pass_context
def export(ctx, output):
    """Export all data to JSON."""
    db = ctx.obj["db"]

    db.export_to_json(output)
    click.echo(click.style(f"✓ Data exported to {output}", fg="green"))


@cli.command()
@click.option("--input", "-i", required=True, help="Input JSON file path")
@click.pass_context
def import_data(ctx, input):
    """Import data from JSON file."""
    db = ctx.obj["db"]

    if not click.confirm(f"This will replace all existing data. Continue?"):
        return

    db.import_from_json(input)
    click.echo(click.style(f"✓ Data imported from {input}", fg="green"))


@cli.command()
@click.option("--output", "-o", help="Backup file path")
@click.pass_context
def backup(ctx, output):
    """Backup database."""
    db = ctx.obj["db"]

    if not output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"task_tracker_backup_{timestamp}.db"

    db.backup_database(output)
    click.echo(click.style(f"✓ Database backed up to {output}", fg="green"))


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def cancel(ctx, task_id):
    """Cancel a task."""
    tracker = ctx.obj["tracker"]

    task = tracker.cancel_task(task_id)

    if not task:
        click.echo(click.style(f"✗ Task {task_id} not found", fg="red"), err=True)
        sys.exit(1)

    click.echo(click.style(f"✓ Task {task_id} cancelled", fg="yellow"))


if __name__ == "__main__":
    cli(obj={})
