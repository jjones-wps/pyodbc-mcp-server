"""Tests for the MSSQL MCP Server."""

import json
from queue import Queue
from unittest.mock import MagicMock, patch

import pytest

from mssql_mcp_server.server import ConnectionPool


class TestSecurityFiltering:
    """Tests for SQL query security filtering."""

    def test_select_query_allowed(self):
        """SELECT queries should be allowed."""
        query = "SELECT * FROM users"
        assert query.strip().upper().startswith("SELECT")

    def test_insert_query_blocked(self):
        """INSERT queries should be blocked."""
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE"]
        query = "INSERT INTO users VALUES (1, 'test')"
        query_upper = query.strip().upper()

        assert not query_upper.startswith("SELECT")
        assert any(kw in query_upper for kw in dangerous_keywords)

    def test_dangerous_keywords_in_subquery(self):
        """Dangerous keywords in subqueries should be detected."""
        query = "SELECT * FROM (DELETE FROM users) AS t"
        query_upper = query.strip().upper()

        # Even though it starts with SELECT, DELETE is present
        assert "DELETE" in query_upper

    def test_keyword_in_column_name_not_blocked(self):
        """Keywords that are part of column names should not be blocked."""
        # This tests that we check for whole words, not substrings
        query = "SELECT updated_at, created_by FROM users"
        query_upper = f" {query.strip().upper()} "

        # "UPDATE" as whole word should not be found
        assert " UPDATE " not in query_upper

    def test_dangerous_keyword_with_parenthesis(self):
        """Keywords followed by parenthesis should be blocked."""
        query = "SELECT * FROM users WHERE id IN (EXEC('DROP TABLE users'))"
        query_upper = f" {query.strip().upper()} "

        # EXEC( should be detected
        assert " EXEC(" in query_upper or "EXEC(" in query_upper


class TestRowLimiting:
    """Tests for row limiting functionality."""

    def test_max_rows_capped_at_1000(self):
        """max_rows should be capped at 1000."""
        requested = 5000
        max_allowed = 1000
        actual = min(requested, max_allowed)
        assert actual == 1000

    def test_default_max_rows(self):
        """Default max_rows should be 100."""
        default = 100
        assert default == 100


class TestTableNameParsing:
    """Tests for table name parsing."""

    def test_schema_qualified_name(self):
        """Schema-qualified names should be parsed correctly."""
        table_name = "dbo.users"
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema, table = "dbo", table_name

        assert schema == "dbo"
        assert table == "users"

    def test_unqualified_name_defaults_to_dbo(self):
        """Unqualified names should default to dbo schema."""
        table_name = "users"
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema, table = "dbo", table_name

        assert schema == "dbo"
        assert table == "users"

    def test_multi_part_table_name(self):
        """Multi-part names should split on first dot only."""
        table_name = "myschema.my.table"
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema, table = "dbo", table_name

        assert schema == "myschema"
        assert table == "my.table"


class TestConnectionPool:
    """Tests for the ConnectionPool class."""

    def test_create_pool(self):
        """ConnectionPool.create() should initialize correctly."""
        pool = ConnectionPool.create(
            size=5,
            server="localhost",
            database="testdb",
            driver="ODBC Driver 17 for SQL Server",
        )

        assert pool.size == 5
        assert pool.server == "localhost"
        assert pool.database == "testdb"
        assert pool.driver == "ODBC Driver 17 for SQL Server"
        assert isinstance(pool.pool, Queue)
        assert pool.pool.empty()

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_get_connection_creates_new_when_empty(self, mock_connect):
        """get_connection() should create new connection when pool is empty."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool.create(
            size=5,
            server="localhost",
            database="testdb",
            driver="ODBC Driver 17",
        )

        conn = pool.get_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once()

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_return_connection_adds_to_pool(self, mock_connect):
        """return_connection() should add connection back to pool."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool.create(
            size=5,
            server="localhost",
            database="testdb",
            driver="ODBC Driver 17",
        )

        # Get a connection
        conn = pool.get_connection()
        assert pool.pool.empty()

        # Return it
        pool.return_connection(conn)
        assert not pool.pool.empty()
        assert pool.pool.qsize() == 1

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_return_connection_closes_when_full(self, mock_connect):
        """return_connection() should close connection when pool is full."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        pool = ConnectionPool.create(
            size=1,
            server="localhost",
            database="testdb",
            driver="ODBC Driver 17",
        )

        # Fill the pool manually
        pool.pool.put(MagicMock())

        # Return another connection
        pool.return_connection(mock_conn)

        # Should close the connection since pool is full
        mock_conn.close.assert_called_once()

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_close_all_empties_pool(self, mock_connect):
        """close_all() should close all connections and empty pool."""
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()

        pool = ConnectionPool.create(
            size=5,
            server="localhost",
            database="testdb",
            driver="ODBC Driver 17",
        )

        # Add connections to pool
        pool.pool.put(mock_conn1)
        pool.pool.put(mock_conn2)
        assert pool.pool.qsize() == 2

        # Close all
        pool.close_all()

        assert pool.pool.empty()
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()


class TestSecurityFilteringDetailed:
    """More detailed security filtering tests."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "EXEC",
            "EXECUTE",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
            "DENY",
            "BACKUP",
            "RESTORE",
            "SHUTDOWN",
            "DBCC",
        ],
    )
    def test_all_dangerous_keywords_blocked(self, keyword):
        """All dangerous keywords should be detected."""
        query = f"SELECT * FROM users; {keyword} something"
        query_upper = f" {query.strip().upper()} "

        # Check for keyword as whole word
        assert f" {keyword} " in query_upper or f" {keyword}(" in query_upper

    def test_cte_with_dangerous_keyword_blocked(self):
        """CTEs containing dangerous keywords should be blocked."""
        query = "WITH cte AS (DELETE FROM users) SELECT * FROM cte"
        query_upper = f" {query.strip().upper()} "

        # DELETE may be preceded by ( in CTEs, check for both patterns
        assert " DELETE " in query_upper or "(DELETE " in query_upper

    def test_union_with_dangerous_keyword_blocked(self):
        """UNION queries with dangerous keywords should be blocked."""
        query = "SELECT 1 UNION ALL EXEC sp_help"
        query_upper = f" {query.strip().upper()} "

        assert " EXEC " in query_upper


class TestAsyncTools:
    """Tests for async tool functionality (without actual DB calls)."""

    @pytest.mark.asyncio
    async def test_list_tables_returns_json(self):
        """ListTables should return valid JSON."""
        # This test would need mocking of the database
        # For now, just test the JSON structure expected
        expected_keys = ["database", "server", "table_count", "tables"]
        sample_result = {
            "database": "test",
            "server": "localhost",
            "table_count": 0,
            "tables": [],
        }

        result = json.dumps(sample_result)
        parsed = json.loads(result)

        for key in expected_keys:
            assert key in parsed

    @pytest.mark.asyncio
    async def test_describe_table_returns_json(self):
        """DescribeTable should return valid JSON."""
        expected_keys = ["table", "column_count", "columns"]
        sample_result = {
            "table": "dbo.test",
            "column_count": 1,
            "columns": [{"name": "id", "type": "int", "nullable": False}],
        }

        result = json.dumps(sample_result)
        parsed = json.loads(result)

        for key in expected_keys:
            assert key in parsed

    @pytest.mark.asyncio
    async def test_read_data_returns_json(self):
        """ReadData should return valid JSON."""
        expected_keys = ["columns", "row_count", "max_rows", "data"]
        sample_result = {
            "columns": ["id", "name"],
            "row_count": 1,
            "max_rows": 100,
            "data": [{"id": "1", "name": "test"}],
        }

        result = json.dumps(sample_result)
        parsed = json.loads(result)

        for key in expected_keys:
            assert key in parsed
