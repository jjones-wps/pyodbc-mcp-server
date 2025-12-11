#!/usr/bin/env python3
"""
MSSQL MCP Server - Read-Only Access to SQL Server via Windows Authentication

A Model Context Protocol (MCP) server that provides safe, read-only access to
Microsoft SQL Server databases using Windows Authentication (Trusted Connection).

Built for environments where:
- Windows Authentication is required (no username/password)
- Read-only access is mandated by IT policy
- SQL Server is accessed from Windows workstations

Features:
- Windows Authentication via pyodbc Trusted_Connection
- Read-only by design: Only SELECT queries allowed
- Security filtering: Blocks INSERT, UPDATE, DELETE, DROP, etc.
- Row limiting: Prevents accidental large result sets
- Claude Code / MCP compatible via FastMCP

Environment Variables:
- MSSQL_SERVER: SQL Server hostname (default: localhost)
- MSSQL_DATABASE: Database name (default: master)
- ODBC_DRIVER: ODBC driver name (default: ODBC Driver 17 for SQL Server)

Author: Jack Jones
License: MIT
"""

import json
import os

import pyodbc
from fastmcp import FastMCP

# Configuration from environment
MSSQL_SERVER = os.environ.get("MSSQL_SERVER", "localhost")
MSSQL_DATABASE = os.environ.get("MSSQL_DATABASE", "master")
ODBC_DRIVER = os.environ.get("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

# Create FastMCP server
mcp = FastMCP("mssql-readonly")


def get_connection() -> pyodbc.Connection:
    """
    Create a database connection using Windows Authentication.

    Uses Trusted_Connection=yes which leverages the current Windows user's
    credentials for authentication. No username/password required.

    Returns:
        pyodbc.Connection: Active database connection

    Raises:
        pyodbc.Error: If connection fails
    """
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=30)


@mcp.tool()
def ListTables(schema_filter: str | None = None) -> str:
    """
    Lists all tables in the SQL Server database.

    Args:
        schema_filter: Optional schema name to filter tables (e.g., 'dbo')

    Returns:
        JSON string with database info and table list
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """
        if schema_filter:
            query += " AND TABLE_SCHEMA = ?"
            cursor.execute(query, (schema_filter,))
        else:
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
            cursor.execute(query)

        tables = []
        for row in cursor.fetchall():
            tables.append(f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}")

        result = {
            "database": MSSQL_DATABASE,
            "server": MSSQL_SERVER,
            "table_count": len(tables),
            "tables": tables[:500],
        }

        if len(tables) > 500:
            result["note"] = (
                f"Showing first 500 of {len(tables)} tables. Use schema_filter to narrow results."
            )

        return json.dumps(result, indent=2)
    finally:
        conn.close()


@mcp.tool()
def DescribeTable(table_name: str) -> str:
    """
    Returns the schema/structure of a specific table.

    Args:
        table_name: Name of the table (can include schema, e.g., 'dbo.oe_hdr')

    Returns:
        JSON string with column definitions
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Parse schema.table format
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        query = """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, (schema, table))

        columns = []
        for row in cursor.fetchall():
            col = {
                "name": row.COLUMN_NAME,
                "type": row.DATA_TYPE,
                "nullable": row.IS_NULLABLE == "YES",
            }
            if row.CHARACTER_MAXIMUM_LENGTH:
                col["max_length"] = row.CHARACTER_MAXIMUM_LENGTH
            if row.NUMERIC_PRECISION:
                col["precision"] = row.NUMERIC_PRECISION
                col["scale"] = row.NUMERIC_SCALE
            if row.COLUMN_DEFAULT:
                col["default"] = row.COLUMN_DEFAULT
            columns.append(col)

        if not columns:
            return json.dumps(
                {"error": f"Table '{table_name}' not found or has no columns."}
            )

        result = {
            "table": f"{schema}.{table}",
            "column_count": len(columns),
            "columns": columns,
        }
        return json.dumps(result, indent=2)
    finally:
        conn.close()


@mcp.tool()
def ReadData(query: str, max_rows: int = 100) -> str:
    """
    Executes a SELECT query and returns results. Only SELECT statements allowed.

    Args:
        query: SQL SELECT query to execute
        max_rows: Maximum rows to return (default: 100, max: 1000)

    Returns:
        JSON string with query results
    """
    # Security: Only allow SELECT statements
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return json.dumps(
            {
                "error": "Security Error: Only SELECT queries are allowed. This server is read-only."
            }
        )

    # Block dangerous keywords that could appear in subqueries or CTEs
    dangerous = [
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
    ]
    for keyword in dangerous:
        # Check for keyword as whole word (not part of column name)
        if f" {keyword} " in f" {query_upper} " or f" {keyword}(" in f" {query_upper} ":
            return json.dumps(
                {
                    "error": f"Security Error: Query contains forbidden keyword '{keyword}'. This server is read-only."
                }
            )

    # Limit rows
    max_rows = min(max_rows, 1000)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch limited rows
        rows = []
        for i, row in enumerate(cursor):
            if i >= max_rows:
                break
            # Convert all values to strings for JSON serialization
            row_dict: dict[str, str | None] = {}
            for col, val in zip(columns, row, strict=True):
                if val is None:
                    row_dict[col] = None
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[col] = val.hex()  # Convert binary to hex string
                else:
                    row_dict[col] = str(val)
            rows.append(row_dict)

        result = {
            "columns": columns,
            "row_count": len(rows),
            "max_rows": max_rows,
            "data": rows,
        }

        if len(rows) == max_rows:
            result["note"] = (
                f"Results limited to {max_rows} rows. Increase max_rows or add WHERE clause."
            )

        return json.dumps(result, indent=2)
    except pyodbc.Error as e:
        return json.dumps({"error": f"Database Error: {str(e)}"})
    finally:
        conn.close()


@mcp.tool()
def ListViews(schema_filter: str | None = None) -> str:
    """
    Lists all views in the SQL Server database.

    Args:
        schema_filter: Optional schema name to filter views (e.g., 'dbo')

    Returns:
        JSON string with database info and view list
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.VIEWS
        """
        if schema_filter:
            query += " WHERE TABLE_SCHEMA = ?"
            cursor.execute(query, (schema_filter,))
        else:
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
            cursor.execute(query)

        views = []
        for row in cursor.fetchall():
            views.append(f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}")

        result = {
            "database": MSSQL_DATABASE,
            "server": MSSQL_SERVER,
            "view_count": len(views),
            "views": views[:500],
        }

        if len(views) > 500:
            result["note"] = (
                f"Showing first 500 of {len(views)} views. Use schema_filter to narrow results."
            )

        return json.dumps(result, indent=2)
    finally:
        conn.close()


@mcp.tool()
def GetTableRelationships(table_name: str) -> str:
    """
    Returns foreign key relationships for a specific table.

    Args:
        table_name: Name of the table (can include schema, e.g., 'dbo.oe_hdr')

    Returns:
        JSON string with incoming and outgoing foreign key relationships
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Parse schema.table format
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema = "dbo"
            table = table_name

        # Get outgoing FKs (this table references others)
        outgoing_query = """
            SELECT
                fk.name AS constraint_name,
                OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
                COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS column_name,
                COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            WHERE OBJECT_NAME(fk.parent_object_id) = ?
              AND OBJECT_SCHEMA_NAME(fk.parent_object_id) = ?
        """
        cursor.execute(outgoing_query, (table, schema))
        outgoing = [
            {
                "constraint": row.constraint_name,
                "column": row.column_name,
                "references_table": row.referenced_table,
                "references_column": row.referenced_column,
            }
            for row in cursor.fetchall()
        ]

        # Get incoming FKs (other tables reference this one)
        incoming_query = """
            SELECT
                fk.name AS constraint_name,
                OBJECT_SCHEMA_NAME(fk.parent_object_id) AS referencing_schema,
                OBJECT_NAME(fk.parent_object_id) AS referencing_table,
                COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS referencing_column,
                COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            WHERE OBJECT_NAME(fk.referenced_object_id) = ?
              AND OBJECT_SCHEMA_NAME(fk.referenced_object_id) = ?
        """
        cursor.execute(incoming_query, (table, schema))
        incoming = [
            {
                "constraint": row.constraint_name,
                "from_table": f"{row.referencing_schema}.{row.referencing_table}",
                "from_column": row.referencing_column,
                "to_column": row.referenced_column,
            }
            for row in cursor.fetchall()
        ]

        result = {
            "table": f"{schema}.{table}",
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming,
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
        }
        return json.dumps(result, indent=2)
    finally:
        conn.close()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
