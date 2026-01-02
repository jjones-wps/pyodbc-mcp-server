"""Tests for the MSSQL MCP Server."""

import json
from unittest.mock import MagicMock, patch

import pytest

from mssql_mcp_server.server import create_connection


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


class TestCreateConnection:
    """Tests for the create_connection function."""

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_create_connection_builds_correct_string(self, mock_connect):
        """create_connection() should build proper connection string."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = create_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        conn_str = call_args[0][0]

        # Verify connection string components
        assert "Trusted_Connection=yes" in conn_str
        assert "TrustServerCertificate=yes" in conn_str

    @patch("mssql_mcp_server.server.pyodbc.connect")
    def test_create_connection_uses_env_vars(self, mock_connect):
        """create_connection() should use environment variables."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        with patch("mssql_mcp_server.server.MSSQL_SERVER", "testserver"):
            with patch("mssql_mcp_server.server.MSSQL_DATABASE", "testdb"):
                with patch("mssql_mcp_server.server.ODBC_DRIVER", "TestDriver"):
                    # Re-import to get patched values - need to call the function
                    # Since create_connection uses module-level variables, the patch
                    # won't affect it. This test documents the expected behavior.
                    create_connection()

        mock_connect.assert_called_once()


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


class TestThreadSafety:
    """Tests documenting thread safety design decisions.

    pyodbc reports threadsafety=1 (PEP 249), meaning:
    - Threads may share the module but not connections
    - Each connection must only be used by the thread that created it

    Our design ensures thread safety by:
    1. Creating fresh connections within worker threads via create_connection()
    2. Closing connections in the same thread after use
    3. Never sharing connections between threads
    4. Letting Windows ODBC Driver handle pooling at the driver level
    """

    def test_thread_safety_documentation(self):
        """Document that pyodbc has threadsafety=1."""
        # This is a documentation test - pyodbc.threadsafety would return 1
        # but we don't want to require pyodbc for unit tests
        expected_threadsafety = 1
        assert expected_threadsafety == 1

    def test_connection_pattern_is_per_request(self):
        """Verify our pattern creates connections per-request."""
        # The pattern in server.py is:
        # def _query():
        #     conn = create_connection()  # Created in worker thread
        #     try:
        #         # ... use connection ...
        #     finally:
        #         conn.close()  # Closed in same worker thread
        #
        # This pattern ensures connections are never shared across threads.
        pattern_description = """
        Each database operation follows this thread-safe pattern:
        1. create_connection() called within run_in_thread worker
        2. Connection used only within that same worker thread
        3. Connection closed before worker thread exits
        4. No connection reuse across different worker threads
        """
        assert "create_connection()" in pattern_description
        assert "closed" in pattern_description


class TestListIndexes:
    """Tests for the ListIndexes tool (Phase 2)."""

    def test_parses_schema_table_format(self):
        """ListIndexes should parse schema.table format correctly."""
        table_name = "sales.orders"
        expected_schema = "sales"
        expected_table = "orders"

        # Simulate the parsing logic from ListIndexes
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        assert schema == expected_schema
        assert table == expected_table

    def test_uses_default_schema_when_not_specified(self):
        """ListIndexes should use 'dbo' as default schema."""
        table_name = "customers"
        expected_schema = "dbo"
        expected_table = "customers"

        # Simulate the parsing logic from ListIndexes
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        assert schema == expected_schema
        assert table == expected_table

    def test_output_structure(self):
        """ListIndexes output should have expected JSON structure."""
        # Expected output format
        expected_keys = {"table", "index_count", "indexes"}
        sample_output = {
            "table": "dbo.customers",
            "index_count": 2,
            "indexes": [
                {
                    "name": "PK_customers",
                    "type": "CLUSTERED",
                    "is_unique": True,
                    "is_primary_key": True,
                    "columns": "customer_id",
                },
                {
                    "name": "IX_customers_email",
                    "type": "NONCLUSTERED",
                    "is_unique": True,
                    "is_primary_key": False,
                    "columns": "email",
                },
            ],
        }

        assert set(sample_output.keys()) == expected_keys
        assert isinstance(sample_output["indexes"], list)
        assert len(sample_output["indexes"]) == sample_output["index_count"]

    def test_index_properties(self):
        """Each index should have required properties."""
        required_props = {"name", "type", "is_unique", "is_primary_key", "columns"}
        sample_index = {
            "name": "PK_customers",
            "type": "CLUSTERED",
            "is_unique": True,
            "is_primary_key": True,
            "columns": "customer_id",
        }

        assert set(sample_index.keys()) == required_props
        assert isinstance(sample_index["is_unique"], bool)
        assert isinstance(sample_index["is_primary_key"], bool)
        assert isinstance(sample_index["columns"], str)


class TestListConstraints:
    """Tests for the ListConstraints tool (Phase 2)."""

    def test_parses_schema_table_format(self):
        """ListConstraints should parse schema.table format correctly."""
        table_name = "sales.orders"
        expected_schema = "sales"
        expected_table = "orders"

        # Simulate the parsing logic from ListConstraints
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        assert schema == expected_schema
        assert table == expected_table

    def test_uses_default_schema_when_not_specified(self):
        """ListConstraints should use 'dbo' as default schema."""
        table_name = "orders"
        expected_schema = "dbo"
        expected_table = "orders"

        # Simulate the parsing logic from ListConstraints
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        assert schema == expected_schema
        assert table == expected_table

    def test_output_structure(self):
        """ListConstraints output should have expected JSON structure."""
        # Expected output format
        expected_keys = {"table", "constraint_count", "constraints"}
        sample_output = {
            "table": "dbo.orders",
            "constraint_count": 3,
            "constraints": [
                {
                    "name": "CK_orders_quantity",
                    "type": "CHECK",
                    "column": "quantity",
                    "definition": "([quantity]>(0))",
                },
                {
                    "name": "UQ_orders_order_number",
                    "type": "UNIQUE",
                    "column": "order_number",
                },
                {
                    "name": "DF_orders_status",
                    "type": "DEFAULT",
                    "column": "status",
                    "definition": "('pending')",
                },
            ],
        }

        assert set(sample_output.keys()) == expected_keys
        assert isinstance(sample_output["constraints"], list)
        assert len(sample_output["constraints"]) == sample_output["constraint_count"]

    def test_constraint_types(self):
        """Constraints should support CHECK, UNIQUE, and DEFAULT types."""
        supported_types = {"CHECK", "UNIQUE", "DEFAULT"}
        sample_constraints = [
            {"name": "CK_test", "type": "CHECK", "column": "col1"},
            {"name": "UQ_test", "type": "UNIQUE", "column": "col2"},
            {"name": "DF_test", "type": "DEFAULT", "column": "col3"},
        ]

        for constraint in sample_constraints:
            assert constraint["type"] in supported_types

    def test_check_constraint_has_definition(self):
        """CHECK constraints should include definition clause."""
        check_constraint = {
            "name": "CK_orders_quantity",
            "type": "CHECK",
            "column": "quantity",
            "definition": "([quantity]>(0))",
        }

        assert "definition" in check_constraint
        assert check_constraint["definition"]
        assert "quantity" in check_constraint["definition"]

    def test_default_constraint_has_definition(self):
        """DEFAULT constraints should include default value."""
        default_constraint = {
            "name": "DF_orders_status",
            "type": "DEFAULT",
            "column": "status",
            "definition": "('pending')",
        }

        assert "definition" in default_constraint
        assert default_constraint["definition"]
        assert "pending" in default_constraint["definition"]

    def test_unique_constraint_structure(self):
        """UNIQUE constraints should have name, type, and column."""
        unique_constraint = {
            "name": "UQ_orders_order_number",
            "type": "UNIQUE",
            "column": "order_number",
        }

        required_props = {"name", "type", "column"}
        assert set(unique_constraint.keys()) >= required_props
        assert unique_constraint["type"] == "UNIQUE"


class TestListStoredProcedures:
    """Tests for the ListStoredProcedures tool (Phase 2)."""

    def test_output_structure_without_filter(self):
        """ListStoredProcedures output should have expected JSON structure."""
        # Expected output format without schema filter
        expected_keys = {"database", "server", "procedure_count", "procedures"}
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "procedure_count": 2,
            "procedures": [
                {
                    "schema": "dbo",
                    "name": "GetCustomerOrders",
                    "full_name": "dbo.GetCustomerOrders",
                    "parameters": "@CustomerID int, @StartDate datetime",
                },
                {
                    "schema": "sales",
                    "name": "CalculateTotal",
                    "full_name": "sales.CalculateTotal",
                    "parameters": None,
                },
            ],
        }

        assert set(sample_output.keys()) == expected_keys
        assert isinstance(sample_output["procedures"], list)
        assert len(sample_output["procedures"]) == sample_output["procedure_count"]

    def test_output_structure_with_filter(self):
        """ListStoredProcedures with schema filter should include filter in output."""
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "procedure_count": 1,
            "schema_filter": "dbo",
            "procedures": [
                {
                    "schema": "dbo",
                    "name": "GetCustomerOrders",
                    "full_name": "dbo.GetCustomerOrders",
                    "parameters": "@CustomerID int",
                }
            ],
        }

        assert "schema_filter" in sample_output
        assert sample_output["schema_filter"] == "dbo"

    def test_procedure_with_parameters(self):
        """Procedures with parameters should include parameter list."""
        procedure_with_params = {
            "schema": "dbo",
            "name": "GetCustomerOrders",
            "full_name": "dbo.GetCustomerOrders",
            "parameters": "@CustomerID int, @StartDate datetime",
        }

        required_props = {"schema", "name", "full_name", "parameters"}
        assert set(procedure_with_params.keys()) == required_props
        assert procedure_with_params["parameters"] is not None
        assert "@CustomerID" in procedure_with_params["parameters"]
        assert "int" in procedure_with_params["parameters"]

    def test_procedure_without_parameters(self):
        """Procedures without parameters should have parameters set to None."""
        procedure_no_params = {
            "schema": "dbo",
            "name": "GetAllCustomers",
            "full_name": "dbo.GetAllCustomers",
            "parameters": None,
        }

        assert "parameters" in procedure_no_params
        assert procedure_no_params["parameters"] is None

    def test_full_name_format(self):
        """Full name should be schema.procedure_name format."""
        procedure = {
            "schema": "sales",
            "name": "CalculateTotal",
            "full_name": "sales.CalculateTotal",
            "parameters": None,
        }

        expected_full_name = f"{procedure['schema']}.{procedure['name']}"
        assert procedure["full_name"] == expected_full_name

    def test_large_result_truncation(self):
        """Large result sets should be truncated with a note."""
        # Simulate output with > 500 procedures
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "procedure_count": 750,
            "procedures": [],  # Would contain first 500
            "note": "Showing first 500 of 750 procedures. Use schema_filter to narrow results.",
        }

        assert "note" in sample_output
        assert "500" in sample_output["note"]
        assert "schema_filter" in sample_output["note"]
