"""Integration tests for MSSQL MCP Server tools with mocked database."""

import json
from unittest.mock import patch

import pytest

import mssql_mcp_server.server as server
from tests.conftest import MockRow


class TestListTablesIntegration:
    """Integration tests for ListTables tool."""

    @pytest.mark.asyncio
    async def test_list_tables_returns_all_tables(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """ListTables should return all tables from database."""
        mock_cursor.fetchall.return_value = sample_tables

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListTables()
            data = json.loads(result)

            assert data["table_count"] == 3
            assert len(data["tables"]) == 3
            assert "dbo.users" in data["tables"]
            assert "dbo.orders" in data["tables"]
            assert "sales.customers" in data["tables"]

    @pytest.mark.asyncio
    async def test_list_tables_with_schema_filter(
        self, mock_connection, mock_cursor, sample_tables
    ):
        """ListTables with schema filter should only return matching tables."""
        # Filter to only dbo tables
        dbo_tables = [t for t in sample_tables if t.TABLE_SCHEMA == "dbo"]
        mock_cursor.fetchall.return_value = dbo_tables

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListTables(schema_filter="dbo")
            data = json.loads(result)

            assert data["table_count"] == 2
            assert "schema_filter" in data
            assert data["schema_filter"] == "dbo"
            assert "dbo.users" in data["tables"]
            assert "dbo.orders" in data["tables"]
            assert "sales.customers" not in data["tables"]


class TestDescribeTableIntegration:
    """Integration tests for DescribeTable tool."""

    @pytest.mark.asyncio
    async def test_describe_table_returns_column_info(
        self, mock_connection, mock_cursor, sample_columns
    ):
        """DescribeTable should return column definitions."""
        # Mock the three queries: columns, PK, FK
        mock_cursor.fetchall.side_effect = [
            sample_columns,  # Column query
            [],  # PK query (no PKs)
            [],  # FK query (no FKs)
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.DescribeTable("dbo.users")
            data = json.loads(result)

            assert data["table"] == "dbo.users"
            assert data["column_count"] == 3
            assert len(data["columns"]) == 3

            # Check first column
            assert data["columns"][0]["name"] == "id"
            assert data["columns"][0]["type"] == "int"
            assert data["columns"][0]["nullable"] is False
            assert data["columns"][0]["is_primary_key"] is False

    @pytest.mark.asyncio
    async def test_describe_table_with_primary_key(
        self, mock_connection, mock_cursor, sample_columns, sample_primary_keys
    ):
        """DescribeTable should mark primary key columns."""
        mock_cursor.fetchall.side_effect = [
            sample_columns,
            sample_primary_keys,  # id is PK
            [],  # No FKs
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.DescribeTable("dbo.users")
            data = json.loads(result)

            # id column should be marked as PK
            id_column = next(c for c in data["columns"] if c["name"] == "id")
            assert id_column["is_primary_key"] is True

            # Other columns should not be PK
            username_column = next(
                c for c in data["columns"] if c["name"] == "username"
            )
            assert username_column["is_primary_key"] is False

    @pytest.mark.asyncio
    async def test_describe_table_with_foreign_key(
        self, mock_connection, mock_cursor, sample_foreign_keys
    ):
        """DescribeTable should include foreign key information."""
        columns_with_fk = [
            MockRow(
                COLUMN_NAME="user_id",
                DATA_TYPE="int",
                IS_NULLABLE="NO",
                CHARACTER_MAXIMUM_LENGTH=None,
                NUMERIC_PRECISION=10,
                NUMERIC_SCALE=0,
                COLUMN_DEFAULT=None,
            )
        ]

        mock_cursor.fetchall.side_effect = [
            columns_with_fk,
            [],  # No PKs
            sample_foreign_keys,  # user_id is FK
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.DescribeTable("dbo.orders")
            data = json.loads(result)

            user_id_column = data["columns"][0]
            assert "foreign_key" in user_id_column
            assert user_id_column["foreign_key"]["references_table"] == "dbo.users"
            assert user_id_column["foreign_key"]["references_column"] == "id"


class TestGetTableRelationshipsIntegration:
    """Integration tests for GetTableRelationships tool."""

    @pytest.mark.asyncio
    async def test_get_relationships_returns_outgoing_and_incoming(
        self, mock_connection, mock_cursor, sample_outgoing_fks, sample_incoming_fks
    ):
        """GetTableRelationships should return both outgoing and incoming FKs."""
        mock_cursor.fetchall.side_effect = [
            sample_outgoing_fks,  # Outgoing FKs
            sample_incoming_fks,  # Incoming FKs
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.GetTableRelationships("dbo.orders")
            data = json.loads(result)

            assert data["table"] == "dbo.orders"
            assert data["outgoing_count"] == 1
            assert data["incoming_count"] == 1

            # Check outgoing relationship
            outgoing = data["outgoing_relationships"][0]
            assert outgoing["constraint"] == "FK_orders_customer_id"
            assert outgoing["columns"] == ["customer_id"]
            assert outgoing["references_table"] == "dbo.customers"
            assert outgoing["references_columns"] == ["id"]
            assert outgoing["on_delete"] == "NO_ACTION"
            assert outgoing["on_update"] == "CASCADE"
            assert outgoing["is_disabled"] is False

            # Check incoming relationship
            incoming = data["incoming_relationships"][0]
            assert incoming["constraint"] == "FK_order_items_order_id"
            assert incoming["from_table"] == "dbo.order_items"
            assert incoming["from_columns"] == ["order_id"]
            assert incoming["to_columns"] == ["id"]

    @pytest.mark.asyncio
    async def test_get_relationships_composite_foreign_key(
        self, mock_connection, mock_cursor, sample_composite_fk
    ):
        """GetTableRelationships should group composite FKs by constraint."""
        mock_cursor.fetchall.side_effect = [
            sample_composite_fk,  # Composite FK (2 columns)
            [],  # No incoming FKs
        ]

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.GetTableRelationships("dbo.order_items")
            data = json.loads(result)

            # Should be grouped into single relationship
            assert data["outgoing_count"] == 1
            outgoing = data["outgoing_relationships"][0]

            assert outgoing["constraint"] == "FK_order_items_product"
            assert len(outgoing["columns"]) == 2
            assert outgoing["columns"] == ["product_id", "warehouse_id"]
            assert len(outgoing["references_columns"]) == 2
            assert outgoing["references_columns"] == ["product_id", "warehouse_id"]


class TestListIndexesIntegration:
    """Integration tests for ListIndexes tool."""

    @pytest.mark.asyncio
    async def test_list_indexes_returns_all_indexes(
        self, mock_connection, mock_cursor, sample_indexes
    ):
        """ListIndexes should return all indexes for a table."""
        mock_cursor.fetchall.return_value = sample_indexes

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListIndexes("dbo.users")
            data = json.loads(result)

            assert data["table"] == "dbo.users"
            assert data["index_count"] == 2
            assert len(data["indexes"]) == 2

            # Check primary key index
            pk_index = next(i for i in data["indexes"] if i["is_primary_key"])
            assert pk_index["name"] == "PK_users"
            assert pk_index["type"] == "CLUSTERED"
            assert pk_index["is_unique"] is True


class TestListConstraintsIntegration:
    """Integration tests for ListConstraints tool."""

    @pytest.mark.asyncio
    async def test_list_constraints_returns_all_types(
        self, mock_connection, mock_cursor, sample_constraints
    ):
        """ListConstraints should return CHECK, UNIQUE, and DEFAULT constraints."""
        mock_cursor.fetchall.return_value = sample_constraints

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListConstraints("dbo.users")
            data = json.loads(result)

            assert data["table"] == "dbo.users"
            assert data["constraint_count"] == 3
            assert len(data["constraints"]) == 3

            # Check for different constraint types
            types = {c["type"] for c in data["constraints"]}
            assert "CHECK" in types
            assert "UNIQUE" in types
            assert "DEFAULT" in types


class TestListStoredProceduresIntegration:
    """Integration tests for ListStoredProcedures tool."""

    @pytest.mark.asyncio
    async def test_list_procedures_returns_all_procedures(
        self, mock_connection, mock_cursor, sample_procedures
    ):
        """ListStoredProcedures should return all stored procedures."""
        mock_cursor.fetchall.return_value = sample_procedures

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListStoredProcedures()
            data = json.loads(result)

            assert data["procedure_count"] == 3
            assert len(data["procedures"]) == 3

            # Check procedure with parameters
            proc_with_params = next(
                p for p in data["procedures"] if p["name"] == "sp_GetUserById"
            )
            assert proc_with_params["parameters"] == "@UserId int"

            # Check procedure without parameters
            proc_no_params = next(
                p for p in data["procedures"] if p["name"] == "sp_DeleteOldRecords"
            )
            assert proc_no_params["parameters"] is None


class TestListFunctionsIntegration:
    """Integration tests for ListFunctions tool."""

    @pytest.mark.asyncio
    async def test_list_functions_returns_all_function_types(
        self, mock_connection, mock_cursor, sample_functions
    ):
        """ListFunctions should return scalar and table-valued functions."""
        mock_cursor.fetchall.return_value = sample_functions

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListFunctions()
            data = json.loads(result)

            assert data["function_count"] == 3
            assert len(data["functions"]) == 3

            # Check for different function types
            types = {f["type"] for f in data["functions"]}
            assert "SQL_SCALAR_FUNCTION" in types
            assert "SQL_INLINE_TABLE_VALUED_FUNCTION" in types
            assert "SQL_TABLE_VALUED_FUNCTION" in types


class TestListTriggersIntegration:
    """Integration tests for ListTriggers tool."""

    @pytest.mark.asyncio
    async def test_list_triggers_returns_all_triggers(
        self, mock_connection, mock_cursor, sample_triggers
    ):
        """ListTriggers should return all database triggers."""
        mock_cursor.fetchall.return_value = sample_triggers

        with patch(
            "mssql_mcp_server.server.create_connection", return_value=mock_connection
        ):
            result = await server.ListTriggers()
            data = json.loads(result)

            assert data["trigger_count"] == 3
            assert len(data["triggers"]) == 3

            # Check AFTER trigger
            after_trigger = next(
                t for t in data["triggers"] if t["name"] == "trg_UpdateTimestamp"
            )
            assert after_trigger["type"] == "AFTER"
            assert after_trigger["is_disabled"] is False

            # Check INSTEAD OF trigger
            instead_trigger = next(
                t for t in data["triggers"] if t["name"] == "trg_InsteadOfDelete"
            )
            assert instead_trigger["type"] == "INSTEAD OF"
            assert instead_trigger["is_disabled"] is True
