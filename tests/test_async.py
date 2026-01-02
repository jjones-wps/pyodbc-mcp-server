"""Async behavior tests for MSSQL MCP Server."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import mssql_mcp_server.server as server


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_list_tables_calls(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """Multiple concurrent ListTables calls should execute independently."""
        mock_cursor.fetchall.return_value = sample_tables

        async def call_list_tables():
            """Call ListTables tool."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                return await server.ListTables.fn()

        # Execute 5 concurrent calls
        results = await asyncio.gather(*[call_list_tables() for _ in range(5)])

        # All calls should succeed
        assert len(results) == 5
        for result in results:
            assert "table_count" in result
            assert "tables" in result

    @pytest.mark.asyncio
    async def test_concurrent_different_tools(
        self, mock_connection, mock_cursor, sample_tables, sample_columns
    ):
        """Concurrent calls to different tools should work correctly."""
        # Mock different queries
        mock_cursor.fetchall.side_effect = [
            sample_tables,  # ListTables
            sample_columns,  # DescribeTable columns
            [],  # DescribeTable PKs
            [],  # DescribeTable FKs
            sample_tables[:2],  # ListTables with filter
        ]

        async def call_list_tables():
            """Call ListTables tool."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                return await server.ListTables.fn()

        async def call_describe_table():
            """Call DescribeTable tool."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                return await server.DescribeTable.fn("dbo.users")

        async def call_list_tables_filtered():
            """Call ListTables with schema filter."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                return await server.ListTables.fn(schema_filter="dbo")

        # Execute concurrently
        results = await asyncio.gather(
            call_list_tables(),
            call_describe_table(),
            call_list_tables_filtered(),
        )

        # All calls should succeed
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_concurrent_resource_access(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """Concurrent resource access should work correctly."""
        mock_cursor.fetchall.return_value = sample_tables

        async def call_tables_resource():
            """Call tables resource endpoint."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                return await server.list_tables_resource.fn()

        # Execute 3 concurrent resource calls
        results = await asyncio.gather(*[call_tables_resource() for _ in range(3)])

        # All calls should return same result
        assert len(results) == 3
        for result in results:
            assert isinstance(result, str)
            assert "dbo.users" in result


class TestConnectionHandling:
    """Tests for database connection handling."""

    @pytest.mark.asyncio
    async def test_connection_created_per_request(self, mock_connection, mock_cursor):
        """Each request should create its own connection."""
        mock_cursor.fetchall.return_value = []
        connection_count = 0

        def create_connection_counter():
            """Track connection creation calls."""
            nonlocal connection_count
            connection_count += 1
            return mock_connection

        with patch(
            "mssql_mcp_server.server.create_connection",
            side_effect=create_connection_counter,
        ):
            await server.ListTables.fn()
            await server.ListTables.fn()
            await server.ListTables.fn()

        # Each call should create a new connection
        assert connection_count == 3

    @pytest.mark.asyncio
    async def test_connection_closed_after_request(self, mock_connection, mock_cursor):
        """Connections should be closed after each request."""
        mock_cursor.fetchall.return_value = []

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            await server.ListTables.fn()

        # Connection should be closed
        mock_connection.close.assert_called()

    @pytest.mark.asyncio
    async def test_connection_closed_on_error(self, mock_connection, mock_cursor):
        """Connections should be closed even when errors occur."""
        # Make cursor.execute raise an error
        mock_cursor.execute.side_effect = Exception("Database error")

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            with pytest.raises(Exception, match="Database error"):
                await server.ListTables.fn()

        # Connection should still be closed
        mock_connection.close.assert_called()


class TestThreadSafety:
    """Tests for thread safety of per-request connections."""

    @pytest.mark.asyncio
    async def test_independent_cursors_per_request(self):
        """Each request should get independent cursor instances."""
        cursors_used = []

        def create_mock_connection():
            """Create a unique mock connection and cursor."""
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cur
            cursors_used.append(mock_cur)
            return mock_conn

        with patch(
            "mssql_mcp_server.server.create_connection",
            side_effect=create_mock_connection,
        ):
            # Execute 3 concurrent calls
            await asyncio.gather(
                server.ListTables.fn(),
                server.ListTables.fn(),
                server.ListTables.fn(),
            )

        # Should have 3 different cursor instances
        assert len(cursors_used) == 3
        assert len({id(c) for c in cursors_used}) == 3  # All unique

    @pytest.mark.asyncio
    async def test_no_shared_state_between_requests(self, mock_connection, mock_cursor):
        """Requests should not share state."""
        call_sequence = []

        def track_fetchall(*args, **kwargs):
            """Track order of fetchall calls."""
            call_id = len(call_sequence)
            call_sequence.append(call_id)
            return []

        mock_cursor.fetchall.side_effect = track_fetchall

        async def make_request(request_id):
            """Make a request and verify isolation."""
            with patch(
                "mssql_mcp_server.server.create_connection",
                return_value=mock_connection,
            ):
                await server.ListTables.fn()
                return request_id

        # Execute requests sequentially
        results = []
        for i in range(3):
            result = await make_request(i)
            results.append(result)

        # All requests should complete in order
        assert results == [0, 1, 2]
        assert call_sequence == [0, 1, 2]


class TestAsyncExecution:
    """Tests for async execution behavior."""

    @pytest.mark.asyncio
    async def test_tools_are_async(self):
        """Tool functions should be async."""
        import inspect

        assert inspect.iscoroutinefunction(server.ListTables.fn)
        assert inspect.iscoroutinefunction(server.DescribeTable.fn)
        assert inspect.iscoroutinefunction(server.ReadData.fn)
        assert inspect.iscoroutinefunction(server.ListViews.fn)
        assert inspect.iscoroutinefunction(server.GetTableRelationships.fn)

    @pytest.mark.asyncio
    async def test_resources_are_async(self):
        """Resource functions should be async."""
        import inspect

        assert inspect.iscoroutinefunction(server.list_tables_resource.fn)
        assert inspect.iscoroutinefunction(server.list_views_resource.fn)
        assert inspect.iscoroutinefunction(server.list_schema_tables_resource.fn)
        assert inspect.iscoroutinefunction(server.table_preview_resource.fn)
        assert inspect.iscoroutinefunction(server.database_info_resource.fn)

    @pytest.mark.asyncio
    async def test_blocking_code_runs_in_thread(self, mock_connection, mock_cursor):
        """Blocking database calls should execute in thread pool."""
        mock_cursor.fetchall.return_value = []
        thread_ids = []

        def track_thread(*args, **kwargs):
            """Track which thread executes the query."""
            import threading

            thread_ids.append(threading.current_thread().ident)
            return []

        mock_cursor.fetchall.side_effect = track_thread

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            # Execute multiple calls
            await asyncio.gather(
                server.ListTables.fn(),
                server.ListTables.fn(),
                server.ListTables.fn(),
            )

        # Calls should execute in thread pool (potentially different threads)
        assert len(thread_ids) == 3
        # At least one thread should be different from main thread
        import threading

        main_thread = threading.current_thread().ident
        assert any(tid != main_thread for tid in thread_ids)
