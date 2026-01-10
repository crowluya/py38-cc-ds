"""
Tests for Connection Pool (T030)

Python 3.8.10 compatible
"""

import pytest
import time
import threading
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch


class TestConnectionPool:
    """Tests for ConnectionPool."""

    def test_create_pool(self):
        """Test creating a connection pool."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)

        assert pool is not None
        assert pool.max_size == 5

    def test_pool_default_size(self):
        """Test pool default size."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool()

        assert pool.max_size == 10  # Default

    def test_acquire_connection(self):
        """Test acquiring a connection."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        conn = pool.acquire()

        assert conn is not None

    def test_release_connection(self):
        """Test releasing a connection."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        conn = pool.acquire()
        pool.release(conn)

        assert pool.available_count == 1

    def test_pool_reuses_connections(self):
        """Test pool reuses released connections."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        conn1 = pool.acquire()
        pool.release(conn1)
        conn2 = pool.acquire()

        assert conn1 is conn2

    def test_pool_max_size_limit(self):
        """Test pool respects max size."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=2)
        pool.set_factory(lambda: Mock())

        conn1 = pool.acquire()
        conn2 = pool.acquire()

        # Third acquire should block or raise
        with pytest.raises(Exception):
            pool.acquire(timeout=0.1)

    def test_pool_context_manager(self):
        """Test pool as context manager."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        with pool.connection() as conn:
            assert conn is not None

        # Connection should be released
        assert pool.available_count == 1


class TestPooledConnection:
    """Tests for PooledConnection wrapper."""

    def test_pooled_connection_wraps(self):
        """Test pooled connection wraps underlying connection."""
        from deep_code.core.connection_pool import PooledConnection

        mock_conn = Mock()
        pooled = PooledConnection(mock_conn)

        assert pooled.connection is mock_conn

    def test_pooled_connection_is_valid(self):
        """Test checking if connection is valid."""
        from deep_code.core.connection_pool import PooledConnection

        mock_conn = Mock()
        pooled = PooledConnection(mock_conn)

        assert pooled.is_valid() is True

    def test_pooled_connection_invalidate(self):
        """Test invalidating a connection."""
        from deep_code.core.connection_pool import PooledConnection

        mock_conn = Mock()
        pooled = PooledConnection(mock_conn)

        pooled.invalidate()

        assert pooled.is_valid() is False


class TestPoolStats:
    """Tests for pool statistics."""

    def test_pool_stats(self):
        """Test getting pool statistics."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        stats = pool.get_stats()

        assert "max_size" in stats
        assert "available" in stats
        assert "in_use" in stats

    def test_pool_stats_after_acquire(self):
        """Test stats after acquiring connection."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        conn = pool.acquire()
        stats = pool.get_stats()

        assert stats["in_use"] == 1

    def test_pool_stats_after_release(self):
        """Test stats after releasing connection."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        conn = pool.acquire()
        pool.release(conn)
        stats = pool.get_stats()

        assert stats["in_use"] == 0
        assert stats["available"] == 1


class TestPoolHealthCheck:
    """Tests for pool health checking."""

    def test_health_check_valid(self):
        """Test health check with valid connections."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())
        pool.set_health_check(lambda c: True)

        conn = pool.acquire()
        pool.release(conn)

        # Health check should pass
        pool.check_health()

        assert pool.available_count == 1

    def test_health_check_removes_invalid(self):
        """Test health check removes invalid connections."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        # Health check always fails
        pool.set_health_check(lambda c: False)

        conn = pool.acquire()
        pool.release(conn)
        pool.check_health()

        assert pool.available_count == 0


class TestPoolTimeout:
    """Tests for pool timeout handling."""

    def test_acquire_with_timeout(self):
        """Test acquire with timeout."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=1)
        pool.set_factory(lambda: Mock())

        conn1 = pool.acquire()

        # Second acquire should timeout
        start = time.time()
        with pytest.raises(Exception):
            pool.acquire(timeout=0.1)
        elapsed = time.time() - start

        assert elapsed >= 0.1

    def test_acquire_waits_for_release(self):
        """Test acquire waits for release."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=1)
        pool.set_factory(lambda: Mock())

        conn1 = pool.acquire()
        released = []

        def release_later():
            time.sleep(0.1)
            pool.release(conn1)
            released.append(True)

        thread = threading.Thread(target=release_later)
        thread.start()

        conn2 = pool.acquire(timeout=1.0)
        thread.join()

        assert len(released) == 1
        assert conn2 is conn1


class TestPoolCleanup:
    """Tests for pool cleanup."""

    def test_pool_close(self):
        """Test closing the pool."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        mock_conn = Mock()
        pool.set_factory(lambda: mock_conn)

        conn = pool.acquire()
        pool.release(conn)
        pool.close()

        assert pool.is_closed

    def test_pool_close_with_cleanup(self):
        """Test pool close calls cleanup function."""
        from deep_code.core.connection_pool import ConnectionPool

        closed_conns = []

        def cleanup(conn):
            closed_conns.append(conn)

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())
        pool.set_cleanup(cleanup)

        conn = pool.acquire()
        pool.release(conn)
        pool.close()

        assert len(closed_conns) == 1


class TestPoolPrewarm:
    """Tests for pool prewarming."""

    def test_prewarm_pool(self):
        """Test prewarming the pool."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5, min_size=3)
        pool.set_factory(lambda: Mock())

        pool.prewarm()

        assert pool.available_count >= 3

    def test_prewarm_respects_max(self):
        """Test prewarm respects max size."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5, min_size=10)
        pool.set_factory(lambda: Mock())

        pool.prewarm()

        assert pool.available_count <= 5


class TestHTTPConnectionPool:
    """Tests for HTTP-specific connection pool."""

    def test_create_http_pool(self):
        """Test creating HTTP connection pool."""
        from deep_code.core.connection_pool import HTTPConnectionPool

        pool = HTTPConnectionPool(
            host="localhost",
            port=8080,
            max_size=5,
        )

        assert pool.host == "localhost"
        assert pool.port == 8080

    def test_http_pool_request(self):
        """Test HTTP pool request."""
        from deep_code.core.connection_pool import HTTPConnectionPool

        pool = HTTPConnectionPool(
            host="localhost",
            port=8080,
            max_size=5,
        )

        # Mock the connection
        with patch.object(pool, "_create_connection") as mock_create:
            mock_conn = Mock()
            mock_create.return_value = mock_conn

            with pool.connection() as conn:
                assert conn is not None


class TestLLMConnectionPool:
    """Tests for LLM client connection pool."""

    def test_create_llm_pool(self):
        """Test creating LLM connection pool."""
        from deep_code.core.connection_pool import LLMConnectionPool

        pool = LLMConnectionPool(
            base_url="http://localhost:8080",
            max_size=3,
        )

        assert pool is not None

    def test_llm_pool_get_client(self):
        """Test getting LLM client from pool."""
        from deep_code.core.connection_pool import LLMConnectionPool

        pool = LLMConnectionPool(
            base_url="http://localhost:8080",
            max_size=3,
        )

        with pool.client() as client:
            assert client is not None


class TestPoolIntegration:
    """Integration tests for connection pool."""

    def test_concurrent_access(self):
        """Test concurrent pool access."""
        from deep_code.core.connection_pool import ConnectionPool

        pool = ConnectionPool(max_size=5)
        pool.set_factory(lambda: Mock())

        results = []
        errors = []

        def worker():
            try:
                # Use timeout to wait for available connection
                conn = pool.acquire(timeout=5.0)
                try:
                    time.sleep(0.01)
                    results.append(conn)
                finally:
                    pool.release(conn)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_pool_with_retry(self):
        """Test pool with retry mechanism."""
        from deep_code.core.connection_pool import ConnectionPool
        from deep_code.core.retry import retry, RetryConfig

        pool = ConnectionPool(max_size=2)
        call_count = [0]

        def factory():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Failed")
            return Mock()

        pool.set_factory(factory)

        @retry(RetryConfig(max_retries=5, base_delay=0.01))
        def get_connection():
            return pool.acquire()

        conn = get_connection()
        assert conn is not None
        assert call_count[0] == 3
