"""
Tests for performance optimization (T018)

Python 3.8.10 compatible
"""

import pytest
import time
import threading
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from deep_code.core.tools.base import Tool, ToolCategory, ToolResult, ToolParameter


# Test fixtures

class SlowTool(Tool):
    """A tool that simulates slow execution."""

    def __init__(self, delay: float = 0.1):
        self._delay = delay

    @property
    def name(self) -> str:
        return "SlowTool"

    @property
    def description(self) -> str:
        return "A slow tool for testing"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def requires_permission(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        time.sleep(self._delay)
        return ToolResult.success_result(self.name, f"Completed after {self._delay}s")


class CacheableTool(Tool):
    """A tool that returns cacheable results."""

    def __init__(self):
        self.call_count = 0

    @property
    def name(self) -> str:
        return "CacheableTool"

    @property
    def description(self) -> str:
        return "A cacheable tool"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self):
        return [
            ToolParameter(name="key", type="string", description="Cache key")
        ]

    @property
    def requires_permission(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        self.call_count += 1
        key = arguments.get("key", "default")
        return ToolResult.success_result(
            self.name,
            f"Result for {key}",
            metadata={"call_count": self.call_count},
        )


class TestToolCache:
    """Tests for tool result caching."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache()
        assert cache.size == 0

    def test_cache_with_max_size(self):
        """Test cache with max size."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache(max_size=100)
        assert cache.max_size == 100

    def test_cache_with_ttl(self):
        """Test cache with TTL."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache(ttl_seconds=60)
        assert cache.ttl_seconds == 60

    def test_cache_set_and_get(self):
        """Test setting and getting cache entries."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache()
        result = ToolResult.success_result("Test", "output")

        cache.set("key1", result)
        cached = cache.get("key1")

        assert cached is not None
        assert cached.output == "output"

    def test_cache_miss(self):
        """Test cache miss."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache()
        cached = cache.get("nonexistent")

        assert cached is None

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache(ttl_seconds=0.1)
        result = ToolResult.success_result("Test", "output")

        cache.set("key1", result)
        time.sleep(0.15)
        cached = cache.get("key1")

        assert cached is None

    def test_cache_eviction_lru(self):
        """Test LRU eviction when cache is full."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache(max_size=2)

        cache.set("key1", ToolResult.success_result("Test", "1"))
        cache.set("key2", ToolResult.success_result("Test", "2"))
        cache.set("key3", ToolResult.success_result("Test", "3"))

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_clear(self):
        """Test clearing cache."""
        from deep_code.core.tools.performance import ToolCache

        cache = ToolCache()
        cache.set("key1", ToolResult.success_result("Test", "1"))
        cache.set("key2", ToolResult.success_result("Test", "2"))

        cache.clear()

        assert cache.size == 0
        assert cache.get("key1") is None

    def test_cache_key_generation(self):
        """Test cache key generation."""
        from deep_code.core.tools.performance import generate_cache_key

        key1 = generate_cache_key("Read", {"file_path": "/tmp/test.txt"})
        key2 = generate_cache_key("Read", {"file_path": "/tmp/test.txt"})
        key3 = generate_cache_key("Read", {"file_path": "/tmp/other.txt"})

        assert key1 == key2
        assert key1 != key3

    def test_cache_key_order_independent(self):
        """Test that cache key is independent of argument order."""
        from deep_code.core.tools.performance import generate_cache_key

        key1 = generate_cache_key("Tool", {"a": 1, "b": 2})
        key2 = generate_cache_key("Tool", {"b": 2, "a": 1})

        assert key1 == key2


class TestCachedExecutor:
    """Tests for cached tool executor."""

    def test_cached_executor_initialization(self):
        """Test cached executor initialization."""
        from deep_code.core.tools.performance import CachedToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        executor = CachedToolExecutor(registry)

        assert executor.cache is not None

    def test_cached_executor_caches_results(self):
        """Test that executor caches results."""
        from deep_code.core.tools.performance import CachedToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        executor = CachedToolExecutor(registry, cache_enabled=True)

        # First call
        result1 = executor.execute("CacheableTool", {"key": "test"})
        # Second call (should be cached)
        result2 = executor.execute("CacheableTool", {"key": "test"})

        assert result1.success is True
        assert result2.success is True
        assert tool.call_count == 1  # Only called once

    def test_cached_executor_different_args_not_cached(self):
        """Test that different arguments are not cached together."""
        from deep_code.core.tools.performance import CachedToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        executor = CachedToolExecutor(registry, cache_enabled=True)

        executor.execute("CacheableTool", {"key": "test1"})
        executor.execute("CacheableTool", {"key": "test2"})

        assert tool.call_count == 2

    def test_cached_executor_cache_disabled(self):
        """Test executor with cache disabled."""
        from deep_code.core.tools.performance import CachedToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        executor = CachedToolExecutor(registry, cache_enabled=False)

        executor.execute("CacheableTool", {"key": "test"})
        executor.execute("CacheableTool", {"key": "test"})

        assert tool.call_count == 2

    def test_cached_executor_skip_cache_for_tool(self):
        """Test skipping cache for specific tools."""
        from deep_code.core.tools.performance import CachedToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        executor = CachedToolExecutor(
            registry,
            cache_enabled=True,
            uncacheable_tools={"CacheableTool"},
        )

        executor.execute("CacheableTool", {"key": "test"})
        executor.execute("CacheableTool", {"key": "test"})

        assert tool.call_count == 2


class TestParallelExecution:
    """Tests for parallel tool execution."""

    def test_parallel_executor_initialization(self):
        """Test parallel executor initialization."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        executor = ParallelToolExecutor(registry)

        assert executor.max_workers > 0

    def test_parallel_executor_with_max_workers(self):
        """Test parallel executor with custom max workers."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        executor = ParallelToolExecutor(registry, max_workers=4)

        assert executor.max_workers == 4

    def test_execute_parallel_single_tool(self):
        """Test parallel execution with single tool."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(SlowTool(delay=0.05))

        executor = ParallelToolExecutor(registry)
        results = executor.execute_parallel([
            ("SlowTool", {}),
        ])

        assert len(results) == 1
        assert results[0].success is True

    def test_execute_parallel_multiple_tools(self):
        """Test parallel execution with multiple tools."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(SlowTool(delay=0.1))

        executor = ParallelToolExecutor(registry, max_workers=3)

        start = time.time()
        results = executor.execute_parallel([
            ("SlowTool", {}),
            ("SlowTool", {}),
            ("SlowTool", {}),
        ])
        elapsed = time.time() - start

        assert len(results) == 3
        assert all(r.success for r in results)
        # Should complete faster than sequential (3 * 0.1 = 0.3s)
        assert elapsed < 0.25

    def test_execute_parallel_preserves_order(self):
        """Test that parallel execution preserves result order."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        executor = ParallelToolExecutor(registry)
        results = executor.execute_parallel([
            ("CacheableTool", {"key": "first"}),
            ("CacheableTool", {"key": "second"}),
            ("CacheableTool", {"key": "third"}),
        ])

        assert "first" in results[0].output
        assert "second" in results[1].output
        assert "third" in results[2].output

    def test_execute_parallel_handles_errors(self):
        """Test that parallel execution handles errors gracefully."""
        from deep_code.core.tools.performance import ParallelToolExecutor
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(CacheableTool())

        executor = ParallelToolExecutor(registry)
        results = executor.execute_parallel([
            ("CacheableTool", {"key": "valid"}),
            ("NonExistent", {}),  # This will fail
            ("CacheableTool", {"key": "also_valid"}),
        ])

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestChunkedFileReader:
    """Tests for chunked file reading."""

    def test_chunked_reader_initialization(self):
        """Test chunked reader initialization."""
        from deep_code.core.tools.performance import ChunkedFileReader

        reader = ChunkedFileReader(chunk_size=1024)
        assert reader.chunk_size == 1024

    def test_chunked_reader_default_chunk_size(self):
        """Test default chunk size."""
        from deep_code.core.tools.performance import ChunkedFileReader

        reader = ChunkedFileReader()
        assert reader.chunk_size > 0

    def test_read_small_file(self, tmp_path):
        """Test reading a small file (no chunking needed)."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        reader = ChunkedFileReader(chunk_size=1024)
        content = reader.read_file(str(test_file))

        assert content == "Hello, World!"

    def test_read_large_file_chunked(self, tmp_path):
        """Test reading a large file in chunks."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "large.txt"
        large_content = "x" * 10000
        test_file.write_text(large_content, encoding="utf-8")

        reader = ChunkedFileReader(chunk_size=1000)
        content = reader.read_file(str(test_file))

        assert content == large_content

    def test_read_file_with_offset(self, tmp_path):
        """Test reading file with offset."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "test.txt"
        test_file.write_text("0123456789", encoding="utf-8")

        reader = ChunkedFileReader()
        content = reader.read_file(str(test_file), offset=5)

        assert content == "56789"

    def test_read_file_with_limit(self, tmp_path):
        """Test reading file with limit."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "test.txt"
        test_file.write_text("0123456789", encoding="utf-8")

        reader = ChunkedFileReader()
        content = reader.read_file(str(test_file), limit=5)

        assert content == "01234"

    def test_read_file_with_offset_and_limit(self, tmp_path):
        """Test reading file with both offset and limit."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "test.txt"
        test_file.write_text("0123456789", encoding="utf-8")

        reader = ChunkedFileReader()
        content = reader.read_file(str(test_file), offset=2, limit=5)

        assert content == "23456"

    def test_read_file_iterator(self, tmp_path):
        """Test reading file as iterator."""
        from deep_code.core.tools.performance import ChunkedFileReader

        test_file = tmp_path / "test.txt"
        test_file.write_text("0123456789", encoding="utf-8")

        reader = ChunkedFileReader(chunk_size=3)
        chunks = list(reader.read_file_chunks(str(test_file)))

        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        assert "".join(chunks) == "0123456789"

    def test_read_nonexistent_file(self):
        """Test reading non-existent file."""
        from deep_code.core.tools.performance import ChunkedFileReader

        reader = ChunkedFileReader()

        with pytest.raises(FileNotFoundError):
            reader.read_file("/nonexistent/file.txt")


class TestPerformanceMetrics:
    """Tests for performance metrics collection."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        assert metrics.total_executions == 0

    def test_record_execution(self):
        """Test recording execution metrics."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_execution("TestTool", 0.1, success=True)

        assert metrics.total_executions == 1
        assert metrics.get_tool_stats("TestTool")["count"] == 1

    def test_record_multiple_executions(self):
        """Test recording multiple executions."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_execution("Tool1", 0.1, success=True)
        metrics.record_execution("Tool1", 0.2, success=True)
        metrics.record_execution("Tool2", 0.3, success=False)

        assert metrics.total_executions == 3
        assert metrics.get_tool_stats("Tool1")["count"] == 2
        assert metrics.get_tool_stats("Tool2")["count"] == 1

    def test_get_average_duration(self):
        """Test getting average duration."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_execution("Tool", 0.1, success=True)
        metrics.record_execution("Tool", 0.2, success=True)
        metrics.record_execution("Tool", 0.3, success=True)

        stats = metrics.get_tool_stats("Tool")
        assert abs(stats["avg_duration"] - 0.2) < 0.01

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_cache_hit("Tool")
        metrics.record_cache_hit("Tool")
        metrics.record_cache_miss("Tool")

        assert metrics.get_cache_hit_rate("Tool") == pytest.approx(2/3, rel=0.01)

    def test_get_summary(self):
        """Test getting metrics summary."""
        from deep_code.core.tools.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_execution("Tool1", 0.1, success=True)
        metrics.record_execution("Tool2", 0.2, success=False)

        summary = metrics.get_summary()

        assert "total_executions" in summary
        assert summary["total_executions"] == 2


class TestPerformanceIntegration:
    """Integration tests for performance features."""

    def test_full_performance_workflow(self):
        """Test full performance optimization workflow."""
        from deep_code.core.tools.performance import (
            CachedToolExecutor,
            PerformanceMetrics,
        )
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = CacheableTool()
        registry.register(tool)

        metrics = PerformanceMetrics()
        executor = CachedToolExecutor(
            registry,
            cache_enabled=True,
            metrics=metrics,
        )

        # Execute multiple times
        executor.execute("CacheableTool", {"key": "test"})
        executor.execute("CacheableTool", {"key": "test"})  # Cache hit
        executor.execute("CacheableTool", {"key": "other"})

        # Check metrics
        assert metrics.total_executions >= 2
        assert tool.call_count == 2  # Only 2 actual executions
