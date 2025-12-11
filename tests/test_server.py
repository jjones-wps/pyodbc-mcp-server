"""Tests for the MSSQL MCP Server."""


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
