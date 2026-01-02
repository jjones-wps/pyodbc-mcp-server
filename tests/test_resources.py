"""Resource endpoint tests for MSSQL MCP Server."""

import json
from unittest.mock import patch

import pytest

import mssql_mcp_server.server as server
from tests.conftest import MockRow


class TestListTablesResource:
    """Tests for mssql://tables resource."""

    @pytest.mark.asyncio
    async def test_list_tables_resource_returns_newline_separated(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """Tables resource should return newline-separated table names."""
        mock_cursor.fetchall.return_value = sample_tables

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_tables_resource.fn()

            # Should be newline-separated text, not JSON
            assert isinstance(result, str)
            lines = result.strip().split("\n")
            assert len(lines) == 3
            assert "dbo.users" in lines
            assert "dbo.orders" in lines
            assert "sales.customers" in lines

    @pytest.mark.asyncio
    async def test_list_tables_resource_empty_database(
        self, mock_connection, mock_cursor
    ):
        """Tables resource should handle empty database."""
        mock_cursor.fetchall.return_value = []

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_tables_resource.fn()

            assert result == ""


class TestListViewsResource:
    """Tests for mssql://views resource."""

    @pytest.mark.asyncio
    async def test_list_views_resource_returns_newline_separated(
        self, mock_connection, mock_cursor
    ):
        """Views resource should return newline-separated view names."""
        sample_views = [
            MockRow(TABLE_SCHEMA="dbo", TABLE_NAME="vw_active_users"),
            MockRow(TABLE_SCHEMA="sales", TABLE_NAME="vw_monthly_totals"),
        ]
        mock_cursor.fetchall.return_value = sample_views

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_views_resource.fn()

            lines = result.strip().split("\n")
            assert len(lines) == 2
            assert "dbo.vw_active_users" in lines
            assert "sales.vw_monthly_totals" in lines

    @pytest.mark.asyncio
    async def test_list_views_resource_empty(self, mock_connection, mock_cursor):
        """Views resource should handle no views."""
        mock_cursor.fetchall.return_value = []

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_views_resource.fn()

            assert result == ""


class TestSchemaTablesResource:
    """Tests for mssql://schema/{schema_name} resource."""

    @pytest.mark.asyncio
    async def test_schema_resource_filters_by_schema(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """Schema resource should only return tables from specified schema."""
        dbo_tables = [t for t in sample_tables if t.TABLE_SCHEMA == "dbo"]
        mock_cursor.fetchall.return_value = dbo_tables

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_schema_tables_resource.fn("dbo")

            lines = result.strip().split("\n")
            assert len(lines) == 2
            # Schema resource returns table names without schema prefix
            assert "users" in lines
            assert "orders" in lines
            assert "customers" not in result

    @pytest.mark.asyncio
    async def test_schema_resource_empty_schema(self, mock_connection, mock_cursor):
        """Schema resource should handle empty schema."""
        mock_cursor.fetchall.return_value = []

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.list_schema_tables_resource.fn("nonexistent")

            assert result == ""


class TestTablePreviewResource:
    """Tests for mssql://table/{table_name}/preview resource."""

    @pytest.mark.asyncio
    async def test_table_preview_returns_json(self, mock_connection, mock_cursor):
        """Table preview should return JSON with columns and sample data."""
        # First query: column metadata
        column_rows = [
            MockRow(COLUMN_NAME="id", DATA_TYPE="int"),
            MockRow(COLUMN_NAME="username", DATA_TYPE="varchar"),
            MockRow(COLUMN_NAME="email", DATA_TYPE="varchar"),
        ]

        # Second query: sample data
        mock_cursor.description = [
            ("id", int, None, None, None, None, None),
            ("username", str, None, None, None, None, None),
            ("email", str, None, None, None, None, None),
        ]
        preview_rows = [
            (1, "alice", "alice@example.com"),
            (2, "bob", "bob@example.com"),
        ]

        # Mock two sequential queries
        mock_cursor.fetchall.side_effect = [
            column_rows,  # First query for columns
            preview_rows,  # Second query for data
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.table_preview_resource.fn("dbo.users")
            data = json.loads(result)

            assert data["table"] == "dbo.users"
            assert data["preview_rows"] == 2
            assert len(data["columns"]) == 3
            assert data["columns"][0]["name"] == "id"
            assert data["columns"][0]["type"] == "int"
            assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_table_preview_empty_table(self, mock_connection, mock_cursor):
        """Table preview should handle empty table."""
        # First query: column metadata
        column_rows = [
            MockRow(COLUMN_NAME="id", DATA_TYPE="int"),
        ]

        # Second query: no data
        mock_cursor.description = [
            ("id", int, None, None, None, None, None),
        ]

        # Mock two sequential queries
        mock_cursor.fetchall.side_effect = [
            column_rows,  # First query for columns
            [],  # Second query returns no data
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.table_preview_resource.fn("dbo.empty_table")
            data = json.loads(result)

            assert data["table"] == "dbo.empty_table"
            assert data["preview_rows"] == 0
            assert data["data"] == []


class TestDatabaseInfoResource:
    """Tests for mssql://info resource."""

    @pytest.mark.asyncio
    async def test_database_info_returns_metadata(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """Database info should return server, database, and table count."""
        # Mock queries for table/view counts and schemas
        mock_cursor.fetchone.side_effect = [
            MockRow(cnt=10),  # table_count
            MockRow(cnt=5),  # view_count
        ]
        mock_cursor.fetchall.return_value = [
            MockRow(TABLE_SCHEMA="dbo"),
            MockRow(TABLE_SCHEMA="sales"),
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.database_info_resource.fn()
            data = json.loads(result)

            assert "server" in data
            assert "database" in data
            assert data["table_count"] == 10
            assert data["view_count"] == 5

    @pytest.mark.asyncio
    async def test_database_info_uses_env_config(
        self, mock_connection, mock_cursor, monkeypatch
    ):
        """Database info should use environment variables for server/database."""
        # Set environment variables
        monkeypatch.setattr(server, "MSSQL_SERVER", "test-server")
        monkeypatch.setattr(server, "MSSQL_DATABASE", "test-db")

        mock_cursor.fetchone.side_effect = [
            MockRow(cnt=0),
            MockRow(cnt=0),
        ]
        mock_cursor.fetchall.return_value = []

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.database_info_resource.fn()
            data = json.loads(result)

            assert data["server"] == "test-server"
            assert data["database"] == "test-db"
