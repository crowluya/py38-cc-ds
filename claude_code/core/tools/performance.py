"""
Performance optimization for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Tool result caching
- Parallel tool execution
- Chunked file reading
- Performance metrics
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

from claude_code.core.tools.base import ToolResult
from claude_code.core.tools.registry import ToolRegistry, ToolNotFoundError


def generate_cache_key(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Generate a cache key for tool execution.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        Cache key string
    """
    # Sort arguments for consistent key generation
    sorted_args = json.dumps(arguments, sort_keys=True, default=str)
    key_data = f"{tool_name}:{sorted_args}"
    return hashlib.md5(key_data.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    """A single cache entry."""
    result: ToolResult
    timestamp: float
    access_count: int = 0


class ToolCache:
    """
    LRU cache for tool results.

    Features:
    - Max size limit with LRU eviction
    - TTL-based expiration
    - Thread-safe operations
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: Optional[float] = None,
    ):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live in seconds (None for no expiration)
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    @property
    def max_size(self) -> int:
        """Get max cache size."""
        return self._max_size

    @property
    def ttl_seconds(self) -> Optional[float]:
        """Get TTL in seconds."""
        return self._ttl_seconds

    @property
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def get(self, key: str) -> Optional[ToolResult]:
        """
        Get a cached result.

        Args:
            key: Cache key

        Returns:
            Cached ToolResult or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if self._ttl_seconds is not None:
                age = time.time() - entry.timestamp
                if age > self._ttl_seconds:
                    del self._cache[key]
                    return None

            # Update access (move to end for LRU)
            entry.access_count += 1
            self._cache.move_to_end(key)

            return entry.result

    def set(self, key: str, result: ToolResult) -> None:
        """
        Set a cache entry.

        Args:
            key: Cache key
            result: ToolResult to cache
        """
        with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # Remove oldest

            self._cache[key] = CacheEntry(
                result=result,
                timestamp=time.time(),
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def remove(self, key: str) -> bool:
        """
        Remove a cache entry.

        Args:
            key: Cache key

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False


class CachedToolExecutor:
    """
    Tool executor with caching support.

    Caches successful tool results to avoid redundant executions.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        cache_enabled: bool = True,
        cache: Optional[ToolCache] = None,
        uncacheable_tools: Optional[Set[str]] = None,
        metrics: Optional["PerformanceMetrics"] = None,
    ):
        """
        Initialize cached executor.

        Args:
            registry: Tool registry
            cache_enabled: Enable caching
            cache: Custom cache instance
            uncacheable_tools: Set of tool names to never cache
            metrics: Performance metrics collector
        """
        self._registry = registry
        self._cache_enabled = cache_enabled
        self._cache = cache or ToolCache()
        self._uncacheable_tools = uncacheable_tools or set()
        self._metrics = metrics

        # Tools that should never be cached (side effects)
        self._default_uncacheable = {
            "Write", "Edit", "Bash", "TodoWrite", "Task",
        }

    @property
    def cache(self) -> ToolCache:
        """Get cache instance."""
        return self._cache

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        skip_cache: bool = False,
    ) -> ToolResult:
        """
        Execute a tool with caching.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            skip_cache: Skip cache for this execution

        Returns:
            ToolResult
        """
        start_time = time.time()

        # Check if cacheable
        should_cache = (
            self._cache_enabled
            and not skip_cache
            and tool_name not in self._uncacheable_tools
            and tool_name not in self._default_uncacheable
        )

        # Try cache first
        if should_cache:
            cache_key = generate_cache_key(tool_name, arguments)
            cached = self._cache.get(cache_key)
            if cached is not None:
                if self._metrics:
                    self._metrics.record_cache_hit(tool_name)
                return cached

            if self._metrics:
                self._metrics.record_cache_miss(tool_name)

        # Execute tool
        try:
            tool = self._registry.get(tool_name)
            result = tool.execute(arguments)
        except ToolNotFoundError:
            result = ToolResult.error_result(
                tool_name,
                f"Tool not found: {tool_name}",
            )
        except Exception as e:
            result = ToolResult.error_result(
                tool_name,
                f"Execution error: {str(e)}",
            )

        # Cache successful results
        if should_cache and result.success:
            self._cache.set(cache_key, result)

        # Record metrics
        if self._metrics:
            duration = time.time() - start_time
            self._metrics.record_execution(tool_name, duration, result.success)

        return result


class ParallelToolExecutor:
    """
    Executor for parallel tool execution.

    Uses thread pool for concurrent tool execution.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        max_workers: int = 4,
        metrics: Optional["PerformanceMetrics"] = None,
    ):
        """
        Initialize parallel executor.

        Args:
            registry: Tool registry
            max_workers: Maximum concurrent workers
            metrics: Performance metrics collector
        """
        self._registry = registry
        self._max_workers = max_workers
        self._metrics = metrics

    @property
    def max_workers(self) -> int:
        """Get max workers."""
        return self._max_workers

    def execute_parallel(
        self,
        tool_calls: List[Tuple[str, Dict[str, Any]]],
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of (tool_name, arguments) tuples

        Returns:
            List of ToolResults in same order as input
        """
        if not tool_calls:
            return []

        results: List[Optional[ToolResult]] = [None] * len(tool_calls)

        def execute_one(index: int, tool_name: str, arguments: Dict[str, Any]) -> Tuple[int, ToolResult]:
            start_time = time.time()
            try:
                tool = self._registry.get(tool_name)
                result = tool.execute(arguments)
            except ToolNotFoundError:
                result = ToolResult.error_result(
                    tool_name,
                    f"Tool not found: {tool_name}",
                )
            except Exception as e:
                result = ToolResult.error_result(
                    tool_name,
                    f"Execution error: {str(e)}",
                )

            if self._metrics:
                duration = time.time() - start_time
                self._metrics.record_execution(tool_name, duration, result.success)

            return index, result

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [
                executor.submit(execute_one, i, name, args)
                for i, (name, args) in enumerate(tool_calls)
            ]

            for future in as_completed(futures):
                index, result = future.result()
                results[index] = result

        return results  # type: ignore


class ChunkedFileReader:
    """
    Chunked file reader for large files.

    Reads files in chunks to avoid memory issues with large files.
    """

    DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize chunked reader.

        Args:
            chunk_size: Size of each chunk in bytes
        """
        self._chunk_size = chunk_size

    @property
    def chunk_size(self) -> int:
        """Get chunk size."""
        return self._chunk_size

    def read_file(
        self,
        file_path: str,
        offset: int = 0,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> str:
        """
        Read a file with optional offset and limit.

        Args:
            file_path: Path to file
            offset: Byte offset to start reading
            limit: Maximum bytes to read
            encoding: File encoding

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(file_path, "r", encoding=encoding) as f:
            if offset > 0:
                f.seek(offset)

            if limit is not None:
                return f.read(limit)
            else:
                return f.read()

    def read_file_chunks(
        self,
        file_path: str,
        encoding: str = "utf-8",
    ) -> Generator[str, None, None]:
        """
        Read a file in chunks.

        Args:
            file_path: Path to file
            encoding: File encoding

        Yields:
            File content chunks

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(file_path, "r", encoding=encoding) as f:
            while True:
                chunk = f.read(self._chunk_size)
                if not chunk:
                    break
                yield chunk

    def read_lines(
        self,
        file_path: str,
        start_line: int = 0,
        max_lines: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> List[str]:
        """
        Read specific lines from a file.

        Args:
            file_path: Path to file
            start_line: Line number to start (0-indexed)
            max_lines: Maximum lines to read
            encoding: File encoding

        Returns:
            List of lines
        """
        lines = []
        with open(file_path, "r", encoding=encoding) as f:
            for i, line in enumerate(f):
                if i < start_line:
                    continue
                if max_lines is not None and len(lines) >= max_lines:
                    break
                lines.append(line)
        return lines


@dataclass
class ToolStats:
    """Statistics for a single tool."""
    count: int = 0
    total_duration: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class PerformanceMetrics:
    """
    Collector for performance metrics.

    Tracks execution times, cache hits, and other performance data.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._tool_stats: Dict[str, ToolStats] = {}
        self._lock = threading.RLock()

    @property
    def total_executions(self) -> int:
        """Get total execution count."""
        with self._lock:
            return sum(s.count for s in self._tool_stats.values())

    def record_execution(
        self,
        tool_name: str,
        duration: float,
        success: bool,
    ) -> None:
        """
        Record a tool execution.

        Args:
            tool_name: Name of the tool
            duration: Execution duration in seconds
            success: Whether execution succeeded
        """
        with self._lock:
            if tool_name not in self._tool_stats:
                self._tool_stats[tool_name] = ToolStats()

            stats = self._tool_stats[tool_name]
            stats.count += 1
            stats.total_duration += duration
            if success:
                stats.success_count += 1
            else:
                stats.failure_count += 1

    def record_cache_hit(self, tool_name: str) -> None:
        """Record a cache hit."""
        with self._lock:
            if tool_name not in self._tool_stats:
                self._tool_stats[tool_name] = ToolStats()
            self._tool_stats[tool_name].cache_hits += 1

    def record_cache_miss(self, tool_name: str) -> None:
        """Record a cache miss."""
        with self._lock:
            if tool_name not in self._tool_stats:
                self._tool_stats[tool_name] = ToolStats()
            self._tool_stats[tool_name].cache_misses += 1

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """
        Get statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary with tool statistics
        """
        with self._lock:
            if tool_name not in self._tool_stats:
                return {"count": 0, "avg_duration": 0.0}

            stats = self._tool_stats[tool_name]
            avg_duration = stats.total_duration / stats.count if stats.count > 0 else 0.0

            return {
                "count": stats.count,
                "avg_duration": avg_duration,
                "total_duration": stats.total_duration,
                "success_count": stats.success_count,
                "failure_count": stats.failure_count,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses,
            }

    def get_cache_hit_rate(self, tool_name: str) -> float:
        """
        Get cache hit rate for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Cache hit rate (0.0 to 1.0)
        """
        with self._lock:
            if tool_name not in self._tool_stats:
                return 0.0

            stats = self._tool_stats[tool_name]
            total = stats.cache_hits + stats.cache_misses
            if total == 0:
                return 0.0

            return stats.cache_hits / total

    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall metrics summary.

        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            total_executions = sum(s.count for s in self._tool_stats.values())
            total_duration = sum(s.total_duration for s in self._tool_stats.values())
            total_success = sum(s.success_count for s in self._tool_stats.values())
            total_cache_hits = sum(s.cache_hits for s in self._tool_stats.values())
            total_cache_misses = sum(s.cache_misses for s in self._tool_stats.values())

            return {
                "total_executions": total_executions,
                "total_duration": total_duration,
                "avg_duration": total_duration / total_executions if total_executions > 0 else 0.0,
                "success_rate": total_success / total_executions if total_executions > 0 else 0.0,
                "cache_hit_rate": total_cache_hits / (total_cache_hits + total_cache_misses) if (total_cache_hits + total_cache_misses) > 0 else 0.0,
                "tools": list(self._tool_stats.keys()),
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tool_stats.clear()
