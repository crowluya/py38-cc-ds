"""
Progress Indicators (T027)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Progress bar with percentage and ETA
- Spinner for indeterminate progress
- Status indicator with icons
- Multi-progress for parallel tasks
- Time estimation
"""

import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TextIO


@dataclass
class ProgressStyle:
    """Style configuration for progress bar."""
    fill_char: str = "█"
    empty_char: str = "░"
    left_bracket: str = "["
    right_bracket: str = "]"

    @classmethod
    def default(cls) -> "ProgressStyle":
        """Get default style."""
        return cls()

    @classmethod
    def simple(cls) -> "ProgressStyle":
        """Get simple ASCII style."""
        return cls(
            fill_char="=",
            empty_char=" ",
            left_bracket="[",
            right_bracket="]",
        )


def format_percentage(current: int, total: int) -> str:
    """
    Format progress as percentage.

    Args:
        current: Current progress
        total: Total progress

    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0%"
    pct = (current / total) * 100
    return f"{pct:.0f}%"


def format_bar(current: int, total: int, width: int = 20) -> str:
    """
    Format progress as a bar.

    Args:
        current: Current progress
        total: Total progress
        width: Bar width in characters

    Returns:
        Formatted bar string
    """
    if total == 0:
        filled = 0
    else:
        filled = int((current / total) * width)

    empty = width - filled
    return "█" * filled + "░" * empty


def format_time(seconds: float) -> str:
    """
    Format time duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.0f}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}:{secs:02d}"

    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}:{secs:02d}"


def format_size(bytes_count: int) -> str:
    """
    Format byte size.

    Args:
        bytes_count: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f}PB"


class ProgressEstimator:
    """Estimates remaining time for progress."""

    def __init__(self) -> None:
        """Initialize estimator."""
        self._start_time: Optional[float] = None
        self._current = 0
        self._total = 100
        self._last_update: Optional[float] = None
        self._speed_samples: List[float] = []

    def update(self, current: int, elapsed: Optional[float] = None) -> None:
        """
        Update progress.

        Args:
            current: Current progress (0-100 or absolute)
            elapsed: Elapsed time in seconds
        """
        if self._start_time is None:
            self._start_time = time.time()

        self._current = current
        self._last_update = elapsed if elapsed is not None else (time.time() - self._start_time)

        # Calculate speed
        if self._last_update > 0 and current > 0:
            speed = current / self._last_update
            self._speed_samples.append(speed)
            # Keep last 10 samples
            if len(self._speed_samples) > 10:
                self._speed_samples = self._speed_samples[-10:]

    def estimate_remaining(self) -> Optional[float]:
        """
        Estimate remaining time.

        Returns:
            Estimated remaining seconds or None
        """
        if not self._speed_samples or self._current >= self._total:
            return None

        avg_speed = sum(self._speed_samples) / len(self._speed_samples)
        if avg_speed <= 0:
            return None

        remaining = self._total - self._current
        return remaining / avg_speed

    def get_speed(self) -> float:
        """
        Get current speed.

        Returns:
            Speed in units per second
        """
        if not self._speed_samples:
            return 0.0
        return sum(self._speed_samples) / len(self._speed_samples)


class ProgressBar:
    """Progress bar with percentage and ETA."""

    def __init__(
        self,
        total: int,
        output: Optional[TextIO] = None,
        description: str = "",
        width: int = 30,
        style: Optional[ProgressStyle] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Initialize progress bar.

        Args:
            total: Total progress value
            output: Output stream
            description: Progress description
            width: Bar width
            style: Progress style
            on_progress: Progress callback
            on_complete: Completion callback
        """
        self._total = total
        self._current = 0
        self._output = output or sys.stdout
        self._description = description
        self._width = width
        self._style = style or ProgressStyle.default()
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._estimator = ProgressEstimator()
        self._estimator._total = total
        self._start_time = time.time()
        self._finished = False

    @property
    def total(self) -> int:
        """Get total."""
        return self._total

    @property
    def current(self) -> int:
        """Get current progress."""
        return self._current

    def update(self, value: int) -> None:
        """
        Update progress to value.

        Args:
            value: New progress value
        """
        self._current = min(value, self._total)
        elapsed = time.time() - self._start_time
        self._estimator.update(self._current, elapsed)

        self._render()

        if self._on_progress:
            try:
                self._on_progress(self._current, self._total)
            except Exception:
                pass

    def increment(self, amount: int = 1) -> None:
        """
        Increment progress.

        Args:
            amount: Amount to increment
        """
        self.update(self._current + amount)

    def finish(self) -> None:
        """Finish progress bar."""
        if self._finished:
            return

        self._finished = True
        self._output.write("\n")
        self._output.flush()

        if self._on_complete:
            try:
                self._on_complete()
            except Exception:
                pass

    def _render(self) -> None:
        """Render progress bar."""
        # Build bar
        if self._total == 0:
            filled = 0
        else:
            filled = int((self._current / self._total) * self._width)

        empty = self._width - filled
        bar = (
            self._style.left_bracket +
            self._style.fill_char * filled +
            self._style.empty_char * empty +
            self._style.right_bracket
        )

        # Build percentage
        pct = format_percentage(self._current, self._total)

        # Build ETA
        remaining = self._estimator.estimate_remaining()
        eta = f" ETA: {format_time(remaining)}" if remaining else ""

        # Build description
        desc = f"{self._description} " if self._description else ""

        # Output
        line = f"\r{desc}{bar} {pct} ({self._current}/{self._total}){eta}"
        self._output.write(line)
        self._output.flush()


class Spinner:
    """Spinner for indeterminate progress."""

    DEFAULT_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ASCII_FRAMES = ["-", "\\", "|", "/"]

    def __init__(
        self,
        output: Optional[TextIO] = None,
        message: str = "",
        frames: Optional[List[str]] = None,
        interval: float = 0.1,
    ) -> None:
        """
        Initialize spinner.

        Args:
            output: Output stream
            message: Spinner message
            frames: Animation frames
            interval: Frame interval in seconds
        """
        self._output = output or sys.stdout
        self._message = message
        self._frames = frames or self.DEFAULT_FRAMES
        self._interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_index = 0

    @property
    def frames(self) -> List[str]:
        """Get animation frames."""
        return self._frames

    def start(self) -> None:
        """Start spinner."""
        if self._running:
            return

        self._running = True
        self._render()

    def stop(self) -> None:
        """Stop spinner."""
        self._running = False
        self._output.write("\r" + " " * (len(self._message) + 10) + "\r")
        self._output.flush()

    def _render(self) -> None:
        """Render current frame."""
        frame = self._frames[self._frame_index % len(self._frames)]
        line = f"\r{frame} {self._message}"
        self._output.write(line)
        self._output.flush()
        self._frame_index += 1

    def __enter__(self) -> "Spinner":
        """Enter context."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context."""
        self.stop()


class StatusIndicator:
    """Status indicator with icons."""

    ICONS = {
        "info": "ℹ",
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "pending": "○",
        "running": "●",
    }

    ASCII_ICONS = {
        "info": "[i]",
        "success": "[+]",
        "error": "[x]",
        "warning": "[!]",
        "pending": "[ ]",
        "running": "[*]",
    }

    def __init__(
        self,
        output: Optional[TextIO] = None,
        use_unicode: bool = True,
    ) -> None:
        """
        Initialize status indicator.

        Args:
            output: Output stream
            use_unicode: Use unicode icons
        """
        self._output = output or sys.stdout
        self._icons = self.ICONS if use_unicode else self.ASCII_ICONS

    def update(self, message: str, status: str = "info") -> None:
        """
        Update status.

        Args:
            message: Status message
            status: Status type
        """
        icon = self._icons.get(status, self._icons["info"])
        self._output.write(f"{icon} {message}\n")
        self._output.flush()

    def success(self, message: str) -> None:
        """Show success status."""
        self.update(message, "success")

    def error(self, message: str) -> None:
        """Show error status."""
        self.update(message, "error")

    def warning(self, message: str) -> None:
        """Show warning status."""
        self.update(message, "warning")

    def info(self, message: str) -> None:
        """Show info status."""
        self.update(message, "info")


@dataclass
class Task:
    """A task in multi-progress."""
    id: str
    description: str
    total: int
    completed: int = 0
    status: str = "pending"


class MultiProgress:
    """Multiple progress bars for parallel tasks."""

    def __init__(self, output: Optional[TextIO] = None) -> None:
        """
        Initialize multi-progress.

        Args:
            output: Output stream
        """
        self._output = output or sys.stdout
        self._tasks: Dict[str, Task] = {}
        self._task_counter = 0

    def add_task(
        self,
        description: str,
        total: int = 100,
    ) -> str:
        """
        Add a task.

        Args:
            description: Task description
            total: Total progress

        Returns:
            Task ID
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"

        self._tasks[task_id] = Task(
            id=task_id,
            description=description,
            total=total,
        )

        return task_id

    def update(
        self,
        task_id: str,
        completed: Optional[int] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Update a task.

        Args:
            task_id: Task ID
            completed: New completed value
            description: New description
        """
        task = self._tasks.get(task_id)
        if not task:
            return

        if completed is not None:
            task.completed = completed
        if description is not None:
            task.description = description

        self._render()

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        return self._tasks.get(task_id)

    def remove_task(self, task_id: str) -> None:
        """
        Remove a task.

        Args:
            task_id: Task ID
        """
        self._tasks.pop(task_id, None)

    def _render(self) -> None:
        """Render all tasks."""
        for task in self._tasks.values():
            pct = format_percentage(task.completed, task.total)
            bar = format_bar(task.completed, task.total, width=20)
            line = f"  {task.description}: {bar} {pct}\n"
            self._output.write(line)
        self._output.flush()


class IndeterminateBar:
    """Indeterminate progress bar (bouncing)."""

    def __init__(
        self,
        output: Optional[TextIO] = None,
        message: str = "",
        width: int = 20,
    ) -> None:
        """
        Initialize indeterminate bar.

        Args:
            output: Output stream
            message: Progress message
            width: Bar width
        """
        self._output = output or sys.stdout
        self._message = message
        self._width = width
        self._position = 0
        self._direction = 1

    def pulse(self) -> None:
        """Pulse the progress bar."""
        # Build bar with bouncing indicator
        bar = [" "] * self._width
        bar[self._position] = "█"

        # Update position
        self._position += self._direction
        if self._position >= self._width - 1:
            self._direction = -1
        elif self._position <= 0:
            self._direction = 1

        bar_str = "".join(bar)
        line = f"\r{self._message} [{bar_str}]"
        self._output.write(line)
        self._output.flush()

    def finish(self) -> None:
        """Finish the bar."""
        self._output.write("\n")
        self._output.flush()


def create_progress_bar(
    total: int,
    description: str = "",
    **kwargs: Any,
) -> ProgressBar:
    """
    Create a progress bar.

    Args:
        total: Total progress
        description: Progress description
        **kwargs: Additional options

    Returns:
        ProgressBar instance
    """
    return ProgressBar(total=total, description=description, **kwargs)


def create_spinner(
    message: str = "",
    **kwargs: Any,
) -> Spinner:
    """
    Create a spinner.

    Args:
        message: Spinner message
        **kwargs: Additional options

    Returns:
        Spinner instance
    """
    return Spinner(message=message, **kwargs)
