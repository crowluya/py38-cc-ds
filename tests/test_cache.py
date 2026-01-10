"""
Tests for Cache System (T031)

Python 3.8.10 compatible
"""

import pytest
import time
import threading
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch


class TestLRUCache:
    """Tests for LRU Cache."""

    def test_create_cache(self):
        """Test creating a cache."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        assert cache is not None
        assert cache.max_size == 100

    def test_cache_get_set(self):
        """Test basic get/set operations."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_miss_with_default(self):
        """Test cache miss with default value."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        result = cache.get("nonexistent", default="default")

        assert result == "default"

    def test_cache_eviction(self):
        """Test LRU eviction."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_cache_access_updates_lru(self):
        """Test accessing item updates LRU order."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # Access "a" to make it recent
        cache.set("d", 4)  # Should evict "b" instead of "a"

        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_cache_delete(self):
        """Test deleting from cache."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        cache.set("key", "value")
        cache.delete("key")

        assert cache.get("key") is None

    def test_cache_clear(self):
        """Test clearing cache."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()

        assert cache.size == 0


class TestTTLCache:
    """Tests for TTL Cache."""

    def test_create_ttl_cache(self):
        """Test creating TTL cache."""
        from deep_code.core.cache import TTLCache

        cache = TTLCache(max_size=100, ttl=60.0)

        assert cache.ttl == 60.0

    def test_ttl_cache_expiration(self):
        """Test TTL expiration."""
        from deep_code.core.cache import TTLCache

        cache = TTLCache(max_size=100, ttl=0.1)

        cache.set("key", "value")
        time.sleep(0.15)

        assert cache.get("key") is None

    def test_ttl_cache_not_expired(self):
        """Test TTL not expired."""
        from deep_code.core.cache import TTLCache

        cache = TTLCache(max_size=100, ttl=10.0)

        cache.set("key", "value")

        assert cache.get("key") == "value"

    def test_ttl_cache_custom_ttl(self):
        """Test custom TTL per item."""
        from deep_code.core.cache import TTLCache

        cache = TTLCache(max_size=100, ttl=10.0)

        cache.set("key", "value", ttl=0.1)
        time.sleep(0.15)

        assert cache.get("key") is None


class TestCacheStats:
    """Tests for cache statistics."""

    def test_cache_stats(self):
        """Test getting cache stats."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        stats = cache.get_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        cache.set("key", "value")
        cache.get("key")  # Hit
        cache.get("key")  # Hit
        cache.get("missing")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1


class TestCacheDecorator:
    """Tests for cache decorator."""

    def test_cached_function(self):
        """Test caching function results."""
        from deep_code.core.cache import cached

        call_count = [0]

        @cached(max_size=100)
        def expensive_func(x):
            call_count[0] += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count[0] == 1  # Only called once

    def test_cached_with_ttl(self):
        """Test cached with TTL."""
        from deep_code.core.cache import cached

        call_count = [0]

        @cached(max_size=100, ttl=0.1)
        def func(x):
            call_count[0] += 1
            return x

        func(1)
        func(1)  # Should use cache
        time.sleep(0.15)
        func(1)  # Should call again

        assert call_count[0] == 2

    def test_cached_different_args(self):
        """Test cached with different arguments."""
        from deep_code.core.cache import cached

        call_count = [0]

        @cached(max_size=100)
        def func(x, y):
            call_count[0] += 1
            return x + y

        func(1, 2)
        func(1, 2)  # Cache hit
        func(2, 3)  # Different args

        assert call_count[0] == 2


class TestFileCache:
    """Tests for file-based cache."""

    def test_create_file_cache(self):
        """Test creating file cache."""
        from deep_code.core.cache import FileCache
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileCache(cache_dir=tmpdir)
            assert cache is not None

    def test_file_cache_get_set(self):
        """Test file cache get/set."""
        from deep_code.core.cache import FileCache
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileCache(cache_dir=tmpdir)

            cache.set("key", "value")
            result = cache.get("key")

            assert result == "value"

    def test_file_cache_persistence(self):
        """Test file cache persists across instances."""
        from deep_code.core.cache import FileCache
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = FileCache(cache_dir=tmpdir)
            cache1.set("key", "value")

            cache2 = FileCache(cache_dir=tmpdir)
            result = cache2.get("key")

            assert result == "value"

    def test_file_cache_delete(self):
        """Test file cache delete."""
        from deep_code.core.cache import FileCache
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileCache(cache_dir=tmpdir)

            cache.set("key", "value")
            cache.delete("key")

            assert cache.get("key") is None


class TestCacheKey:
    """Tests for cache key generation."""

    def test_make_key_simple(self):
        """Test simple key generation."""
        from deep_code.core.cache import make_cache_key

        key = make_cache_key("func", (1, 2), {"a": 3})

        assert isinstance(key, str)
        assert len(key) > 0

    def test_make_key_deterministic(self):
        """Test key generation is deterministic."""
        from deep_code.core.cache import make_cache_key

        key1 = make_cache_key("func", (1, 2), {"a": 3})
        key2 = make_cache_key("func", (1, 2), {"a": 3})

        assert key1 == key2

    def test_make_key_different_args(self):
        """Test different args produce different keys."""
        from deep_code.core.cache import make_cache_key

        key1 = make_cache_key("func", (1,), {})
        key2 = make_cache_key("func", (2,), {})

        assert key1 != key2


class TestCacheNamespace:
    """Tests for cache namespaces."""

    def test_cache_with_namespace(self):
        """Test cache with namespace."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100, namespace="test")

        cache.set("key", "value")

        assert cache.get("key") == "value"

    def test_different_namespaces(self):
        """Test different namespaces are isolated."""
        from deep_code.core.cache import LRUCache

        cache1 = LRUCache(max_size=100, namespace="ns1")
        cache2 = LRUCache(max_size=100, namespace="ns2")

        cache1.set("key", "value1")
        cache2.set("key", "value2")

        assert cache1.get("key") == "value1"
        assert cache2.get("key") == "value2"


class TestCacheThreadSafety:
    """Tests for cache thread safety."""

    def test_concurrent_access(self):
        """Test concurrent cache access."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=1000)
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    key = f"key_{thread_id}_{i}"
                    cache.set(key, i)
                    cache.get(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCacheIntegration:
    """Integration tests for cache."""

    def test_cache_with_llm_response(self):
        """Test caching LLM responses."""
        from deep_code.core.cache import LRUCache

        cache = LRUCache(max_size=100)

        # Simulate LLM response
        response = {
            "content": "Hello, world!",
            "finish_reason": "stop",
        }

        cache.set("prompt_hash", response)
        cached = cache.get("prompt_hash")

        assert cached == response

    def test_cache_with_file_content(self):
        """Test caching file content."""
        from deep_code.core.cache import TTLCache

        cache = TTLCache(max_size=100, ttl=300.0)

        content = "file content here"
        cache.set("/path/to/file", content)

        assert cache.get("/path/to/file") == content
