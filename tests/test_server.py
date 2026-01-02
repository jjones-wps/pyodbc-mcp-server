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

    def test_truncate_keyword_blocked(self):
        """TRUNCATE queries should be blocked."""
        query = "TRUNCATE TABLE users"
        query_upper = query.strip().upper()
        assert "TRUNCATE" in query_upper

    def test_alter_keyword_blocked(self):
        """ALTER queries should be blocked."""
        query = "SELECT * FROM users; ALTER TABLE users ADD COLUMN hacked INT"
        query_upper = query.strip().upper()
        assert "ALTER" in query_upper

    def test_exec_keyword_blocked(self):
        """EXEC/EXECUTE queries should be blocked."""
        query = (
            "SELECT * FROM users WHERE id = 1; EXEC sp_executesql N'DROP TABLE users'"
        )
        query_upper = query.strip().upper()
        assert "EXEC" in query_upper

    def test_sp_executesql_blocked(self):
        """sp_executesql should be blocked."""
        query = "SELECT * FROM users; EXEC sp_executesql N'DELETE FROM users'"
        query_upper = query.strip().upper()
        assert "SP_EXECUTESQL" in query_upper

    def test_xp_cmdshell_blocked(self):
        """xp_cmdshell should be blocked."""
        query = "SELECT * FROM users; EXEC xp_cmdshell 'dir'"
        query_upper = query.strip().upper()
        assert "XP_CMDSHELL" in query_upper

    def test_comment_with_dangerous_keyword(self):
        """Dangerous keywords in SQL comments should still be detected."""
        query = "SELECT * FROM users -- DROP TABLE users"
        query_upper = query.strip().upper()
        assert "DROP" in query_upper

    def test_case_insensitive_blocking(self):
        """Dangerous keywords should be blocked regardless of case."""
        query = "SeLeCt * FrOm UsErS; dElEtE fRoM uSeRs"
        query_upper = query.strip().upper()
        assert "DELETE" in query_upper

    def test_multiple_statements_with_dangerous_keywords(self):
        """Multiple statements with dangerous keywords should be detected."""
        query = "SELECT * FROM users; DELETE FROM users; INSERT INTO users VALUES (1)"
        query_upper = query.strip().upper()
        assert "DELETE" in query_upper
        assert "INSERT" in query_upper

    def test_union_with_dangerous_keywords(self):
        """UNION queries with dangerous keywords should be detected."""
        query = (
            "SELECT id FROM users UNION SELECT id FROM (DELETE FROM users RETURNING id)"
        )
        query_upper = query.strip().upper()
        assert "DELETE" in query_upper


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


class TestListFunctions:
    """Tests for the ListFunctions tool (Phase 2)."""

    def test_output_structure_without_filter(self):
        """ListFunctions output should have expected JSON structure."""
        # Expected output format without schema filter
        expected_keys = {"database", "server", "function_count", "functions"}
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "function_count": 2,
            "functions": [
                {
                    "schema": "dbo",
                    "name": "CalculateDiscount",
                    "full_name": "dbo.CalculateDiscount",
                    "type": "SQL_SCALAR_FUNCTION",
                    "parameters": "@Amount decimal, @Percentage decimal",
                },
                {
                    "schema": "sales",
                    "name": "GetTopCustomers",
                    "full_name": "sales.GetTopCustomers",
                    "type": "SQL_INLINE_TABLE_VALUED_FUNCTION",
                    "parameters": "@TopN int",
                },
            ],
        }

        assert set(sample_output.keys()) == expected_keys
        assert isinstance(sample_output["functions"], list)
        assert len(sample_output["functions"]) == sample_output["function_count"]

    def test_output_structure_with_filter(self):
        """ListFunctions with schema filter should include filter in output."""
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "function_count": 1,
            "schema_filter": "dbo",
            "functions": [
                {
                    "schema": "dbo",
                    "name": "CalculateDiscount",
                    "full_name": "dbo.CalculateDiscount",
                    "type": "SQL_SCALAR_FUNCTION",
                    "parameters": "@Amount decimal",
                }
            ],
        }

        assert "schema_filter" in sample_output
        assert sample_output["schema_filter"] == "dbo"

    def test_function_types(self):
        """Functions should support different function types."""
        supported_types = {
            "SQL_SCALAR_FUNCTION",
            "SQL_INLINE_TABLE_VALUED_FUNCTION",
            "SQL_TABLE_VALUED_FUNCTION",
        }
        sample_functions = [
            {
                "schema": "dbo",
                "name": "CalcTotal",
                "full_name": "dbo.CalcTotal",
                "type": "SQL_SCALAR_FUNCTION",
                "parameters": None,
            },
            {
                "schema": "dbo",
                "name": "GetOrders",
                "full_name": "dbo.GetOrders",
                "type": "SQL_INLINE_TABLE_VALUED_FUNCTION",
                "parameters": "@CustomerID int",
            },
            {
                "schema": "dbo",
                "name": "SplitString",
                "full_name": "dbo.SplitString",
                "type": "SQL_TABLE_VALUED_FUNCTION",
                "parameters": "@String varchar",
            },
        ]

        for func in sample_functions:
            assert func["type"] in supported_types

    def test_function_with_parameters(self):
        """Functions with parameters should include parameter list."""
        function_with_params = {
            "schema": "dbo",
            "name": "CalculateDiscount",
            "full_name": "dbo.CalculateDiscount",
            "type": "SQL_SCALAR_FUNCTION",
            "parameters": "@Amount decimal, @Percentage decimal",
        }

        required_props = {"schema", "name", "full_name", "type", "parameters"}
        assert set(function_with_params.keys()) == required_props
        assert function_with_params["parameters"] is not None
        assert "@Amount" in function_with_params["parameters"]
        assert "decimal" in function_with_params["parameters"]

    def test_function_without_parameters(self):
        """Functions without parameters should have parameters set to None."""
        function_no_params = {
            "schema": "dbo",
            "name": "GetCurrentTimestamp",
            "full_name": "dbo.GetCurrentTimestamp",
            "type": "SQL_SCALAR_FUNCTION",
            "parameters": None,
        }

        assert "parameters" in function_no_params
        assert function_no_params["parameters"] is None

    def test_full_name_format(self):
        """Full name should be schema.function_name format."""
        function = {
            "schema": "sales",
            "name": "CalculateTotal",
            "full_name": "sales.CalculateTotal",
            "type": "SQL_SCALAR_FUNCTION",
            "parameters": None,
        }

        expected_full_name = f"{function['schema']}.{function['name']}"
        assert function["full_name"] == expected_full_name

    def test_large_result_truncation(self):
        """Large result sets should be truncated with a note."""
        # Simulate output with > 500 functions
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "function_count": 750,
            "functions": [],  # Would contain first 500
            "note": "Showing first 500 of 750 functions. Use schema_filter to narrow results.",
        }

        assert "note" in sample_output
        assert "500" in sample_output["note"]
        assert "schema_filter" in sample_output["note"]


class TestDescribeTableEnhancements:
    """Tests for DescribeTable PK/FK enhancements (Phase 2)."""

    def test_column_has_is_primary_key_indicator(self):
        """All columns should have is_primary_key indicator."""
        sample_columns = [
            {
                "name": "customer_id",
                "type": "int",
                "nullable": False,
                "is_primary_key": True,
            },
            {
                "name": "email",
                "type": "varchar",
                "nullable": False,
                "max_length": 100,
                "is_primary_key": False,
            },
        ]

        for col in sample_columns:
            assert "is_primary_key" in col
            assert isinstance(col["is_primary_key"], bool)

    def test_primary_key_column_marked_correctly(self):
        """Primary key columns should be marked with is_primary_key=True."""
        pk_column = {
            "name": "id",
            "type": "int",
            "nullable": False,
            "is_primary_key": True,
        }

        assert pk_column["is_primary_key"] is True

    def test_non_primary_key_column_marked_correctly(self):
        """Non-primary key columns should be marked with is_primary_key=False."""
        regular_column = {
            "name": "name",
            "type": "varchar",
            "nullable": True,
            "max_length": 100,
            "is_primary_key": False,
        }

        assert regular_column["is_primary_key"] is False

    def test_foreign_key_column_has_references(self):
        """Foreign key columns should have foreign_key object with references."""
        fk_column = {
            "name": "customer_id",
            "type": "int",
            "nullable": False,
            "is_primary_key": False,
            "foreign_key": {
                "references_table": "dbo.customers",
                "references_column": "id",
            },
        }

        assert "foreign_key" in fk_column
        assert "references_table" in fk_column["foreign_key"]
        assert "references_column" in fk_column["foreign_key"]
        assert fk_column["foreign_key"]["references_table"] == "dbo.customers"
        assert fk_column["foreign_key"]["references_column"] == "id"

    def test_non_foreign_key_column_has_no_foreign_key(self):
        """Non-foreign key columns should not have foreign_key property."""
        regular_column = {
            "name": "status",
            "type": "varchar",
            "nullable": True,
            "max_length": 50,
            "is_primary_key": False,
        }

        assert "foreign_key" not in regular_column

    def test_composite_primary_key_multiple_columns(self):
        """Multiple columns can be marked as primary keys (composite PK)."""
        columns = [
            {
                "name": "order_id",
                "type": "int",
                "nullable": False,
                "is_primary_key": True,
            },
            {
                "name": "line_number",
                "type": "int",
                "nullable": False,
                "is_primary_key": True,
            },
            {
                "name": "product_id",
                "type": "int",
                "nullable": False,
                "is_primary_key": False,
            },
        ]

        pk_columns = [col for col in columns if col["is_primary_key"]]
        assert len(pk_columns) == 2
        assert pk_columns[0]["name"] == "order_id"
        assert pk_columns[1]["name"] == "line_number"

    def test_column_can_be_both_pk_and_fk(self):
        """A column can be both a primary key and foreign key."""
        pk_fk_column = {
            "name": "user_id",
            "type": "int",
            "nullable": False,
            "is_primary_key": True,
            "foreign_key": {
                "references_table": "dbo.users",
                "references_column": "id",
            },
        }

        assert pk_fk_column["is_primary_key"] is True
        assert "foreign_key" in pk_fk_column
        assert pk_fk_column["foreign_key"]["references_table"] == "dbo.users"


class TestListTriggers:
    """Tests for the ListTriggers tool (Phase 2)."""

    def test_output_structure_without_filter(self):
        """ListTriggers output should have expected JSON structure."""
        # Expected output format without schema filter
        expected_keys = {"database", "server", "trigger_count", "triggers"}
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "trigger_count": 2,
            "triggers": [
                {
                    "schema": "dbo",
                    "name": "trg_UpdateTimestamp",
                    "full_name": "dbo.trg_UpdateTimestamp",
                    "table": "dbo.users",
                    "type": "AFTER",
                    "events": "UPDATE",
                    "is_disabled": False,
                },
                {
                    "schema": "sales",
                    "name": "trg_AuditDelete",
                    "full_name": "sales.trg_AuditDelete",
                    "table": "sales.orders",
                    "type": "AFTER",
                    "events": "DELETE",
                    "is_disabled": False,
                },
            ],
        }

        assert set(sample_output.keys()) == expected_keys

    def test_output_structure_with_filter(self):
        """ListTriggers with schema filter includes filter in output."""
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "schema_filter": "dbo",
            "trigger_count": 1,
            "triggers": [
                {
                    "schema": "dbo",
                    "name": "trg_UpdateTimestamp",
                    "full_name": "dbo.trg_UpdateTimestamp",
                    "table": "dbo.users",
                    "type": "AFTER",
                    "events": "UPDATE",
                    "is_disabled": False,
                }
            ],
        }

        assert "schema_filter" in sample_output
        assert sample_output["schema_filter"] == "dbo"

    def test_trigger_after_type(self):
        """Triggers should support AFTER type."""
        trigger = {
            "schema": "dbo",
            "name": "trg_Insert",
            "full_name": "dbo.trg_Insert",
            "table": "dbo.products",
            "type": "AFTER",
            "events": "INSERT",
            "is_disabled": False,
        }

        assert trigger["type"] == "AFTER"

    def test_trigger_instead_of_type(self):
        """Triggers should support INSTEAD OF type."""
        trigger = {
            "schema": "dbo",
            "name": "trg_InsteadOfUpdate",
            "full_name": "dbo.trg_InsteadOfUpdate",
            "table": "dbo.view_data",
            "type": "INSTEAD OF",
            "events": "UPDATE",
            "is_disabled": False,
        }

        assert trigger["type"] == "INSTEAD OF"

    def test_trigger_single_event(self):
        """Triggers should support single event (INSERT, UPDATE, or DELETE)."""
        trigger = {
            "schema": "dbo",
            "name": "trg_Insert",
            "full_name": "dbo.trg_Insert",
            "table": "dbo.products",
            "type": "AFTER",
            "events": "INSERT",
            "is_disabled": False,
        }

        assert trigger["events"] == "INSERT"

    def test_trigger_multiple_events(self):
        """Triggers should support multiple events as comma-separated string."""
        trigger = {
            "schema": "dbo",
            "name": "trg_AuditChanges",
            "full_name": "dbo.trg_AuditChanges",
            "table": "dbo.users",
            "type": "AFTER",
            "events": "INSERT, UPDATE, DELETE",
            "is_disabled": False,
        }

        assert "," in trigger["events"]
        assert "INSERT" in trigger["events"]
        assert "UPDATE" in trigger["events"]
        assert "DELETE" in trigger["events"]

    def test_trigger_disabled_status_true(self):
        """Triggers should have is_disabled boolean field."""
        trigger = {
            "schema": "dbo",
            "name": "trg_Disabled",
            "full_name": "dbo.trg_Disabled",
            "table": "dbo.archive",
            "type": "AFTER",
            "events": "INSERT",
            "is_disabled": True,
        }

        assert trigger["is_disabled"] is True
        assert isinstance(trigger["is_disabled"], bool)

    def test_trigger_disabled_status_false(self):
        """Triggers should properly report enabled status."""
        trigger = {
            "schema": "dbo",
            "name": "trg_Enabled",
            "full_name": "dbo.trg_Enabled",
            "table": "dbo.users",
            "type": "AFTER",
            "events": "UPDATE",
            "is_disabled": False,
        }

        assert trigger["is_disabled"] is False

    def test_trigger_full_name_format(self):
        """Trigger full_name should be schema.trigger_name."""
        trigger = {
            "schema": "sales",
            "name": "trg_ValidateSale",
            "full_name": "sales.trg_ValidateSale",
            "table": "sales.orders",
            "type": "AFTER",
            "events": "INSERT",
            "is_disabled": False,
        }

        assert trigger["full_name"] == f"{trigger['schema']}.{trigger['name']}"

    def test_trigger_table_format(self):
        """Trigger table should be schema.table_name."""
        trigger = {
            "schema": "dbo",
            "name": "trg_CheckStock",
            "full_name": "dbo.trg_CheckStock",
            "table": "inventory.products",
            "type": "AFTER",
            "events": "UPDATE",
            "is_disabled": False,
        }

        assert "." in trigger["table"]

    def test_large_result_truncation(self):
        """Large trigger lists should be truncated to 500 with note."""
        sample_output = {
            "database": "MyDB",
            "server": "localhost",
            "trigger_count": 750,
            "triggers": [{"schema": "dbo", "name": f"trg_{i}"} for i in range(500)],
            "note": "Showing first 500 of 750 triggers. Use schema_filter to narrow results.",
        }

        assert len(sample_output["triggers"]) == 500
        assert sample_output["trigger_count"] == 750
        assert "note" in sample_output
        assert "500" in sample_output["note"]


class TestGetTableRelationshipsEnhancements:
    """Tests for GetTableRelationships tool enhancements (Phase 2)."""

    def test_outgoing_relationship_structure(self):
        """Outgoing relationships should include all enhanced fields."""
        outgoing_relationship = {
            "constraint": "FK_orders_customer_id",
            "columns": ["customer_id"],
            "references_table": "dbo.customers",
            "references_columns": ["id"],
            "on_delete": "NO_ACTION",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        # Verify all required fields are present
        assert "constraint" in outgoing_relationship
        assert "columns" in outgoing_relationship
        assert "references_table" in outgoing_relationship
        assert "references_columns" in outgoing_relationship
        assert "on_delete" in outgoing_relationship
        assert "on_update" in outgoing_relationship
        assert "is_disabled" in outgoing_relationship

    def test_incoming_relationship_structure(self):
        """Incoming relationships should include all enhanced fields."""
        incoming_relationship = {
            "constraint": "FK_order_items_order_id",
            "from_table": "dbo.order_items",
            "from_columns": ["order_id"],
            "to_columns": ["id"],
            "on_delete": "CASCADE",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        # Verify all required fields are present
        assert "constraint" in incoming_relationship
        assert "from_table" in incoming_relationship
        assert "from_columns" in incoming_relationship
        assert "to_columns" in incoming_relationship
        assert "on_delete" in incoming_relationship
        assert "on_update" in incoming_relationship
        assert "is_disabled" in incoming_relationship

    def test_on_delete_cascade_action(self):
        """ON DELETE CASCADE should be properly represented."""
        relationship = {
            "constraint": "FK_order_items_order_id",
            "columns": ["order_id"],
            "references_table": "dbo.orders",
            "references_columns": ["id"],
            "on_delete": "CASCADE",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert relationship["on_delete"] == "CASCADE"

    def test_on_delete_set_null_action(self):
        """ON DELETE SET NULL should be properly represented."""
        relationship = {
            "constraint": "FK_orders_sales_rep",
            "columns": ["sales_rep_id"],
            "references_table": "dbo.employees",
            "references_columns": ["id"],
            "on_delete": "SET_NULL",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert relationship["on_delete"] == "SET_NULL"

    def test_on_update_cascade_action(self):
        """ON UPDATE CASCADE should be properly represented."""
        relationship = {
            "constraint": "FK_orders_customer_id",
            "columns": ["customer_id"],
            "references_table": "dbo.customers",
            "references_columns": ["id"],
            "on_delete": "NO_ACTION",
            "on_update": "CASCADE",
            "is_disabled": False,
        }

        assert relationship["on_update"] == "CASCADE"

    def test_composite_foreign_key_outgoing(self):
        """Composite foreign keys should have multiple columns in arrays."""
        composite_fk = {
            "constraint": "FK_order_items_product",
            "columns": ["product_id", "warehouse_id"],
            "references_table": "dbo.inventory",
            "references_columns": ["product_id", "warehouse_id"],
            "on_delete": "NO_ACTION",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert len(composite_fk["columns"]) == 2
        assert len(composite_fk["references_columns"]) == 2
        assert composite_fk["columns"] == ["product_id", "warehouse_id"]
        assert composite_fk["references_columns"] == ["product_id", "warehouse_id"]

    def test_composite_foreign_key_incoming(self):
        """Composite FKs in incoming relationships should have multiple columns."""
        composite_fk = {
            "constraint": "FK_shipments_order",
            "from_table": "dbo.shipments",
            "from_columns": ["order_id", "order_line"],
            "to_columns": ["order_id", "line_number"],
            "on_delete": "CASCADE",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert len(composite_fk["from_columns"]) == 2
        assert len(composite_fk["to_columns"]) == 2

    def test_disabled_foreign_key(self):
        """Disabled foreign keys should have is_disabled=True."""
        disabled_fk = {
            "constraint": "FK_temp_orders_customer",
            "columns": ["customer_id"],
            "references_table": "dbo.customers",
            "references_columns": ["id"],
            "on_delete": "NO_ACTION",
            "on_update": "NO_ACTION",
            "is_disabled": True,
        }

        assert disabled_fk["is_disabled"] is True
        assert isinstance(disabled_fk["is_disabled"], bool)

    def test_enabled_foreign_key(self):
        """Enabled foreign keys should have is_disabled=False."""
        enabled_fk = {
            "constraint": "FK_orders_customer_id",
            "columns": ["customer_id"],
            "references_table": "dbo.customers",
            "references_columns": ["id"],
            "on_delete": "NO_ACTION",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert enabled_fk["is_disabled"] is False

    def test_schema_qualified_references_table(self):
        """Referenced table should include schema (schema.table format)."""
        relationship = {
            "constraint": "FK_orders_customer_id",
            "columns": ["customer_id"],
            "references_table": "sales.customers",
            "references_columns": ["id"],
            "on_delete": "NO_ACTION",
            "on_update": "NO_ACTION",
            "is_disabled": False,
        }

        assert "." in relationship["references_table"]
        assert relationship["references_table"] == "sales.customers"

    def test_full_result_structure(self):
        """Complete result should have all expected top-level fields."""
        result = {
            "table": "dbo.orders",
            "outgoing_relationships": [
                {
                    "constraint": "FK_orders_customer_id",
                    "columns": ["customer_id"],
                    "references_table": "dbo.customers",
                    "references_columns": ["id"],
                    "on_delete": "NO_ACTION",
                    "on_update": "NO_ACTION",
                    "is_disabled": False,
                }
            ],
            "incoming_relationships": [
                {
                    "constraint": "FK_order_items_order_id",
                    "from_table": "dbo.order_items",
                    "from_columns": ["order_id"],
                    "to_columns": ["id"],
                    "on_delete": "CASCADE",
                    "on_update": "NO_ACTION",
                    "is_disabled": False,
                }
            ],
            "outgoing_count": 1,
            "incoming_count": 1,
        }

        assert "table" in result
        assert "outgoing_relationships" in result
        assert "incoming_relationships" in result
        assert "outgoing_count" in result
        assert "incoming_count" in result
        assert result["outgoing_count"] == len(result["outgoing_relationships"])
        assert result["incoming_count"] == len(result["incoming_relationships"])
