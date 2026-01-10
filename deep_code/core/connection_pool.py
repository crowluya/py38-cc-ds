"""
Connection Pool (T030)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Generic connection pool
- Thread-safe connection management
- Health checking
- Connection prewarming
- HTTP and LLM specific pools
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar


T = TypeVar("T")


class PoolExhaustedError(Exception):
    """Raised when pool is exhausted and timeout expires."""
    pass


class PoolClosedError(Exception):
    """Raised when trying to use a closed pool."""
    pass


@dataclass
class PooledConnection(Generic[T]):
    """Wrapper for a pooled connection."""
    _connection: T
    _valid: bool = True
    _created_at: float = field(default_factory=time.time)
    _last_used: float = field(default_factory=time.time)

    @property
    def connection(self) -> T:
        """Get the underlying connection."""
        return self._connection

    def is_valid(self) -> bool:
        """Check if connection is valid."""
        return self._valid

    def invalidate(self) -> None:
        """Mark connection as invalid."""
        self._valid = False

    def touch(self) -> None:
        """Update last used time."""
        self._last_used = time.time()

    @property
    def age(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self._created_at

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self._last_used


class ConnectionPool(Generic[T]):
    """
    Generic connection pool.

    Thread-safe pool for managing reusable connections.
    """

    def __init__(
        self,
        max_size: int = 10,
        min_size: int = 0,
        max_idle_time: float = 300.0,
        max_lifetime: float = 3600.0,
    ) -> None:
        """
        Initialize connection pool.

        Args:
            max_size: Maximum pool size
            min_size: Minimum pool size (for prewarming)
            max_idle_time: Max idle time before eviction
            max_lifetime: Max connection lifetime
        """
        self._max_size = max_size
        self._min_size = min(min_size, max_size)
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime

        self._available: List[PooledConnection[T]] = []
        self._in_use: Dict[int, PooledConnection[T]] = {}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._closed = False

        self._factory: Optional[Callable[[], T]] = None
        self._health_check: Optional[Callable[[T], bool]] = None
        self._cleanup: Optional[Callable[[T], None]] = None

        # Stats
        self._total_created = 0
        self._total_destroyed = 0

    @property
    def max_size(self) -> int:
        """Get max pool size."""
        return self._max_size

    @property
    def available_count(self) -> int:
        """Get number of available connections."""
        with self._lock:
            return len(self._available)

    @property
    def in_use_count(self) -> int:
        """Get number of in-use connections."""
        with self._lock:
            return len(self._in_use)

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    def set_factory(self, factory: Callable[[], T]) -> None:
        """Set connection factory."""
        self._factory = factory

    def set_health_check(self, check: Callable[[T], bool]) -> None:
        """Set health check function."""
        self._health_check = check

    def set_cleanup(self, cleanup: Callable[[T], None]) -> None:
        """Set cleanup function."""
        self._cleanup = cleanup

    def acquire(self, timeout: Optional[float] = None) -> PooledConnection[T]:
        """
        Acquire a connection from the pool.

        Args:
            timeout: Max time to wait for connection

        Returns:
            PooledConnection wrapper

        Raises:
            PoolExhaustedError: If timeout expires
            PoolClosedError: If pool is closed
        """
        deadline = time.time() + timeout if timeout is not None else None

        with self._condition:
            while True:
                if self._closed:
                    raise PoolClosedError("Pool is closed")

                # Try to get from available
                while self._available:
                    conn = self._available.pop(0)
                    if conn.is_valid():
                        conn.touch()
                        self._in_use[id(conn)] = conn
                        return conn
                    else:
                        self._destroy_connection(conn)

                # Try to create new
                total = len(self._available) + len(self._in_use)
                if total < self._max_size:
                    conn = self._create_connection()
                    self._in_use[id(conn)] = conn
                    return conn

                # Wait for release
                if deadline is not None:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise PoolExhaustedError(
                            f"Pool exhausted, max_size={self._max_size}"
                        )
                    self._condition.wait(remaining)
                else:
                    raise PoolExhaustedError(
                        f"Pool exhausted, max_size={self._max_size}"
                    )

    def release(self, conn: PooledConnection[T]) -> None:
        """
        Release a connection back to the pool.

        Args:
            conn: Connection to release
        """
        with self._condition:
            conn_id = id(conn)
            if conn_id in self._in_use:
                del self._in_use[conn_id]

            if self._closed or not conn.is_valid():
                self._destroy_connection(conn)
            else:
                conn.touch()
                self._available.append(conn)

            self._condition.notify()

    @contextmanager
    def connection(self) -> Iterator[PooledConnection[T]]:
        """
        Context manager for connection.

        Yields:
            PooledConnection wrapper
        """
        conn = self.acquire()
        try:
            yield conn
        finally:
            self.release(conn)

    def _create_connection(self) -> PooledConnection[T]:
        """Create a new connection."""
        if self._factory is None:
            raise ValueError("No connection factory set")

        raw_conn = self._factory()
        self._total_created += 1
        return PooledConnection(raw_conn)

    def _destroy_connection(self, conn: PooledConnection[T]) -> None:
        """Destroy a connection."""
        if self._cleanup:
            try:
                self._cleanup(conn.connection)
            except Exception:
                pass
        self._total_destroyed += 1

    def check_health(self) -> None:
        """Check health of available connections."""
        with self._lock:
            valid = []
            for conn in self._available:
                if self._is_connection_healthy(conn):
                    valid.append(conn)
                else:
                    self._destroy_connection(conn)
            self._available = valid

    def _is_connection_healthy(self, conn: PooledConnection[T]) -> bool:
        """Check if a connection is healthy."""
        if not conn.is_valid():
            return False

        if conn.age > self._max_lifetime:
            return False

        if conn.idle_time > self._max_idle_time:
            return False

        if self._health_check:
            try:
                return self._health_check(conn.connection)
            except Exception:
                return False

        return True

    def prewarm(self) -> None:
        """Prewarm the pool to min_size."""
        with self._lock:
            current = len(self._available) + len(self._in_use)
            needed = min(self._min_size, self._max_size) - current

            for _ in range(needed):
                try:
                    conn = self._create_connection()
                    self._available.append(conn)
                except Exception:
                    break

    def close(self) -> None:
        """Close the pool and all connections."""
        with self._lock:
            self._closed = True

            # Destroy available connections
            for conn in self._available:
                self._destroy_connection(conn)
            self._available = []

            # Note: in-use connections will be destroyed when released

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Statistics dictionary
        """
        with self._lock:
            return {
                "max_size": self._max_size,
                "min_size": self._min_size,
                "available": len(self._available),
                "in_use": len(self._in_use),
                "total_created": self._total_created,
                "total_destroyed": self._total_destroyed,
                "closed": self._closed,
            }


class HTTPConnectionPool:
    """HTTP connection pool."""

    def __init__(
        self,
        host: str,
        port: int = 80,
        max_size: int = 10,
        timeout: float = 30.0,
        use_ssl: bool = False,
    ) -> None:
        """
        Initialize HTTP connection pool.

        Args:
            host: Target host
            port: Target port
            max_size: Maximum connections
            timeout: Connection timeout
            use_ssl: Use HTTPS
        """
        self._host = host
        self._port = port
        self._timeout = timeout
        self._use_ssl = use_ssl

        self._pool: ConnectionPool[Any] = ConnectionPool(max_size=max_size)
        self._pool.set_factory(self._create_connection)
        self._pool.set_cleanup(self._close_connection)

    @property
    def host(self) -> str:
        """Get host."""
        return self._host

    @property
    def port(self) -> int:
        """Get port."""
        return self._port

    def _create_connection(self) -> Any:
        """Create HTTP connection."""
        if self._use_ssl:
            import http.client
            return http.client.HTTPSConnection(
                self._host,
                self._port,
                timeout=self._timeout,
            )
        else:
            import http.client
            return http.client.HTTPConnection(
                self._host,
                self._port,
                timeout=self._timeout,
            )

    def _close_connection(self, conn: Any) -> None:
        """Close HTTP connection."""
        try:
            conn.close()
        except Exception:
            pass

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Get a connection from the pool."""
        with self._pool.connection() as pooled:
            yield pooled.connection

    def close(self) -> None:
        """Close the pool."""
        self._pool.close()


class LLMConnectionPool:
    """LLM client connection pool."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        max_size: int = 5,
        timeout: float = 60.0,
    ) -> None:
        """
        Initialize LLM connection pool.

        Args:
            base_url: LLM API base URL
            api_key: API key
            max_size: Maximum clients
            timeout: Request timeout
        """
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

        self._pool: ConnectionPool[Any] = ConnectionPool(max_size=max_size)
        self._pool.set_factory(self._create_client)

    def _create_client(self) -> Any:
        """Create LLM client."""
        # Return a simple client wrapper
        return LLMClientWrapper(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
        )

    @contextmanager
    def client(self) -> Iterator[Any]:
        """Get a client from the pool."""
        with self._pool.connection() as pooled:
            yield pooled.connection

    def close(self) -> None:
        """Close the pool."""
        self._pool.close()


class LLMClientWrapper:
    """Simple LLM client wrapper for pooling."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize client wrapper."""
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

    def chat_completion(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Any:
        """Make chat completion request."""
        # Placeholder - actual implementation would use requests
        return {"content": "", "finish_reason": "stop"}

    def close(self) -> None:
        """Close the client."""
        pass


def create_connection_pool(
    max_size: int = 10,
    factory: Optional[Callable[[], Any]] = None,
    **kwargs: Any,
) -> ConnectionPool[Any]:
    """
    Create a connection pool.

    Args:
        max_size: Maximum pool size
        factory: Connection factory
        **kwargs: Additional options

    Returns:
        ConnectionPool instance
    """
    pool: ConnectionPool[Any] = ConnectionPool(max_size=max_size, **kwargs)
    if factory:
        pool.set_factory(factory)
    return pool
