"""
Cache System (T031)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- LRU Cache with size limit
- TTL Cache with expiration
- File-based persistent cache
- Cache decorator
- Thread-safe operations
"""

import functools
import hashlib
import json
import os
import pickle
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with metadata."""
    value: T
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update access count."""
        self.access_count += 1


class LRUCache(Generic[T]):
    """
    LRU (Least Recently Used) Cache.

    Thread-safe cache with size limit and LRU eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        namespace: str = "",
    ) -> None:
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            namespace: Cache namespace
        """
        self._max_size = max_size
        self._namespace = namespace
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.Lock()

        # Stats
        self._hits = 0
        self._misses = 0

    @property
    def max_size(self) -> int:
        """Get max size."""
        return self._max_size

    @property
    def size(self) -> int:
        """Get current size."""
        with self._lock:
            return len(self._cache)

    def _make_key(self, key: str) -> str:
        """Make namespaced key."""
        if self._namespace:
            return f"{self._namespace}:{key}"
        return key

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        full_key = self._make_key(key)

        with self._lock:
            if full_key not in self._cache:
                self._misses += 1
                return default

            entry = self._cache[full_key]

            # Check expiration
            if entry.is_expired():
                del self._cache[full_key]
                self._misses += 1
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(full_key)
            entry.touch()
            self._hits += 1

            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        full_key = self._make_key(key)
        expires_at = time.time() + ttl if ttl else None

        with self._lock:
            # Remove if exists
            if full_key in self._cache:
                del self._cache[full_key]

            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # Add new entry
            self._cache[full_key] = CacheEntry(
                value=value,
                expires_at=expires_at,
            )

    def delete(self, key: str) -> bool:
        """
        Delete from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        full_key = self._make_key(key)

        with self._lock:
            if full_key in self._cache:
                del self._cache[full_key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def has(self, key: str) -> bool:
        """Check if key exists."""
        full_key = self._make_key(key)

        with self._lock:
            if full_key not in self._cache:
                return False
            entry = self._cache[full_key]
            return not entry.is_expired()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "namespace": self._namespace,
            }


class TTLCache(LRUCache[T]):
    """
    TTL (Time To Live) Cache.

    LRU cache with default TTL for all entries.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl: float = 300.0,
        namespace: str = "",
    ) -> None:
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum entries
            ttl: Default TTL in seconds
            namespace: Cache namespace
        """
        super().__init__(max_size=max_size, namespace=namespace)
        self._default_ttl = ttl

    @property
    def ttl(self) -> float:
        """Get default TTL."""
        return self._default_ttl

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None,
    ) -> None:
        """
        Set value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL override (uses default if None)
        """
        actual_ttl = ttl if ttl is not None else self._default_ttl
        super().set(key, value, ttl=actual_ttl)


class FileCache:
    """
    File-based persistent cache.

    Stores cache entries as files on disk.
    """

    def __init__(
        self,
        cache_dir: str,
        ttl: Optional[float] = None,
    ) -> None:
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cache files
            ttl: Default TTL in seconds
        """
        self._cache_dir = cache_dir
        self._ttl = ttl
        self._lock = threading.Lock()

        # Create directory if needed
        os.makedirs(cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        """Convert key to file path."""
        # Hash the key for safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self._cache_dir, f"{key_hash}.cache")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value

        Returns:
            Cached value or default
        """
        path = self._key_to_path(key)

        with self._lock:
            if not os.path.exists(path):
                return default

            try:
                with open(path, "rb") as f:
                    entry = pickle.load(f)

                # Check expiration
                if entry.get("expires_at") and time.time() > entry["expires_at"]:
                    os.remove(path)
                    return default

                return entry["value"]
            except Exception:
                return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL override
        """
        path = self._key_to_path(key)
        actual_ttl = ttl if ttl is not None else self._ttl
        expires_at = time.time() + actual_ttl if actual_ttl else None

        entry = {
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at,
        }

        with self._lock:
            try:
                with open(path, "wb") as f:
                    pickle.dump(entry, f)
            except Exception:
                pass

    def delete(self, key: str) -> bool:
        """
        Delete from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        path = self._key_to_path(key)

        with self._lock:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    return True
                except Exception:
                    pass
            return False

    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            for filename in os.listdir(self._cache_dir):
                if filename.endswith(".cache"):
                    try:
                        os.remove(os.path.join(self._cache_dir, filename))
                    except Exception:
                        pass


def make_cache_key(
    func_name: str,
    args: tuple,
    kwargs: Dict[str, Any],
) -> str:
    """
    Generate cache key from function call.

    Args:
        func_name: Function name
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create a hashable representation
    key_parts = [func_name]

    for arg in args:
        try:
            key_parts.append(repr(arg))
        except Exception:
            key_parts.append(str(id(arg)))

    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={repr(v)}")
        except Exception:
            key_parts.append(f"{k}={id(v)}")

    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    max_size: int = 1000,
    ttl: Optional[float] = None,
    key_func: Optional[Callable[..., str]] = None,
) -> Callable:
    """
    Decorator to cache function results.

    Args:
        max_size: Maximum cache size
        ttl: Time to live in seconds
        key_func: Custom key generation function

    Returns:
        Decorated function
    """
    if ttl:
        cache: LRUCache[Any] = TTLCache(max_size=max_size, ttl=ttl)
    else:
        cache = LRUCache(max_size=max_size)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = make_cache_key(func.__name__, args, kwargs)

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(key, result)

            return result

        # Expose cache for testing
        wrapper.cache = cache  # type: ignore
        return wrapper

    return decorator


def create_cache(
    cache_type: str = "lru",
    **kwargs: Any,
) -> LRUCache[Any]:
    """
    Create a cache instance.

    Args:
        cache_type: Type of cache ("lru", "ttl", "file")
        **kwargs: Cache options

    Returns:
        Cache instance
    """
    if cache_type == "ttl":
        return TTLCache(**kwargs)
    elif cache_type == "file":
        return FileCache(**kwargs)  # type: ignore
    else:
        return LRUCache(**kwargs)
