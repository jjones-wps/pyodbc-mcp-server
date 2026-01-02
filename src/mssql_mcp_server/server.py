#!/usr/bin/env python3
"""MSSQL MCP Server - Read-Only Access to SQL Server via Windows Authentication.

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
- Async non-blocking architecture
- Per-request connections (thread-safe by design)
- MCP Resources for schema discovery

Thread Safety:
pyodbc reports threadsafety=1 (PEP 249), meaning threads may share the module
but not connections. This server creates fresh connections per-request within
worker threads, ensuring connections are never shared across threads. Windows
ODBC Driver handles connection pooling at the driver level transparently.

Environment Variables:
- MSSQL_SERVER: SQL Server hostname (default: localhost)
- MSSQL_DATABASE: Database name (default: master)
- ODBC_DRIVER: ODBC driver name (default: ODBC Driver 17 for SQL Server)

Author: Jack Jones
License: MIT
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
import pyodbc
from fastmcp import FastMCP

# Configure logging
logger = logging.getLogger("mssql_mcp_server")

# Configuration from environment
MSSQL_SERVER = os.environ.get("MSSQL_SERVER", "localhost")
MSSQL_DATABASE = os.environ.get("MSSQL_DATABASE", "master")
ODBC_DRIVER = os.environ.get("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

# Connection settings
CONNECTION_TIMEOUT = int(os.environ.get("MSSQL_CONNECTION_TIMEOUT", "30"))


def create_connection() -> pyodbc.Connection:
    """Create a new database connection.

    Creates a fresh connection using Windows Authentication.
    Windows ODBC Driver handles connection pooling at the driver level,
    so we don't need application-level pooling.
    """
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=CONNECTION_TIMEOUT)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Lifespan context manager for server startup/shutdown.

    Logs server initialization and cleanup. Connection pooling is handled
    transparently by the Windows ODBC Driver at the driver level.
    """
    logger.info(
        f"Starting MSSQL MCP Server: server={MSSQL_SERVER}, database={MSSQL_DATABASE}"
    )
    logger.info(
        "Using per-request connections (ODBC driver handles pooling at driver level)"
    )

    yield {"server": MSSQL_SERVER, "database": MSSQL_DATABASE}

    logger.info("Shutting down MSSQL MCP Server")


# Create FastMCP server with lifespan
mcp: FastMCP = FastMCP("mssql-readonly", lifespan=lifespan)


async def run_in_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking function in a thread pool."""
    return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool()
async def ListTables(schema_filter: str | None = None) -> str:
    """List all tables in the SQL Server database.

    Args:
        schema_filter: Optional schema name to filter tables (e.g., 'dbo')

    Returns:
        JSON string with database info and table list

    """
    logger.debug(f"ListTables called with schema_filter={schema_filter}")

    def _query() -> list[str]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
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
            return tables
        finally:
            conn.close()

    tables = await run_in_thread(_query)

    result: dict[str, Any] = {
        "database": MSSQL_DATABASE,
        "server": MSSQL_SERVER,
        "table_count": len(tables),
        "tables": tables[:500],
    }

    if len(tables) > 500:
        result["note"] = (
            f"Showing first 500 of {len(tables)} tables. "
            "Use schema_filter to narrow results."
        )

    logger.debug(f"Found {len(tables)} tables")
    return json.dumps(result, indent=2)


@mcp.tool()
async def DescribeTable(table_name: str) -> str:
    """Return the schema/structure of a specific table.

    Args:
        table_name: Name of the table (can include schema, e.g., 'dbo.oe_hdr')

    Returns:
        JSON string with column definitions

    """
    logger.debug(f"DescribeTable called for {table_name}")

    # Parse schema.table format
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        schema = "dbo"
        table = table_name

    def _query() -> list[dict[str, Any]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
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
                col: dict[str, Any] = {
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
            return columns
        finally:
            conn.close()

    columns = await run_in_thread(_query)

    if not columns:
        return json.dumps(
            {"error": f"Table '{table_name}' not found or has no columns."}
        )

    result = {
        "table": f"{schema}.{table}",
        "column_count": len(columns),
        "columns": columns,
    }

    logger.debug(f"Found {len(columns)} columns for {table_name}")
    return json.dumps(result, indent=2)


@mcp.tool()
async def ReadData(query: str, max_rows: int = 100) -> str:
    """Execute a SELECT query and return results. Only SELECT statements allowed.

    Args:
        query: SQL SELECT query to execute
        max_rows: Maximum rows to return (default: 100, max: 1000)

    Returns:
        JSON string with query results

    """
    logger.debug(f"ReadData called with max_rows={max_rows}")

    # Security: Only allow SELECT statements
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        logger.warning("Blocked non-SELECT query attempt")
        return json.dumps(
            {
                "error": "Security Error: Only SELECT queries are allowed. "
                "This server is read-only."
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
            logger.warning(f"Blocked query with forbidden keyword: {keyword}")
            return json.dumps(
                {
                    "error": f"Security Error: Query contains forbidden keyword "
                    f"'{keyword}'. This server is read-only."
                }
            )

    # Limit rows
    max_rows = min(max_rows, 1000)

    def _execute() -> tuple[list[str], list[dict[str, str | None]]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description]

            # Fetch limited rows
            rows: list[dict[str, str | None]] = []
            for i, row in enumerate(cursor):
                if i >= max_rows:
                    break
                # Convert all values to strings for JSON serialization
                row_dict: dict[str, str | None] = {}
                for col, val in zip(columns, row, strict=True):
                    if val is None:
                        row_dict[col] = None
                    elif isinstance(val, bytes | bytearray):
                        row_dict[col] = val.hex()  # Convert binary to hex string
                    else:
                        row_dict[col] = str(val)
                rows.append(row_dict)
            return columns, rows
        finally:
            conn.close()

    try:
        columns, rows = await run_in_thread(_execute)
    except pyodbc.Error as e:
        logger.error(f"Database error: {e!s}")
        return json.dumps({"error": f"Database Error: {e!s}"})

    result: dict[str, Any] = {
        "columns": columns,
        "row_count": len(rows),
        "max_rows": max_rows,
        "data": rows,
    }

    if len(rows) == max_rows:
        result["note"] = (
            f"Results limited to {max_rows} rows. "
            "Increase max_rows or add WHERE clause."
        )

    logger.debug(f"Query returned {len(rows)} rows")
    return json.dumps(result, indent=2)


@mcp.tool()
async def ListViews(schema_filter: str | None = None) -> str:
    """List all views in the SQL Server database.

    Args:
        schema_filter: Optional schema name to filter views (e.g., 'dbo')

    Returns:
        JSON string with database info and view list

    """
    logger.debug(f"ListViews called with schema_filter={schema_filter}")

    def _query() -> list[str]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
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
            return views
        finally:
            conn.close()

    views = await run_in_thread(_query)

    result: dict[str, Any] = {
        "database": MSSQL_DATABASE,
        "server": MSSQL_SERVER,
        "view_count": len(views),
        "views": views[:500],
    }

    if len(views) > 500:
        result["note"] = (
            f"Showing first 500 of {len(views)} views. "
            "Use schema_filter to narrow results."
        )

    logger.debug(f"Found {len(views)} views")
    return json.dumps(result, indent=2)


@mcp.tool()
async def GetTableRelationships(table_name: str) -> str:
    """Return foreign key relationships for a specific table.

    Args:
        table_name: Name of the table (can include schema, e.g., 'dbo.oe_hdr')

    Returns:
        JSON string with incoming and outgoing foreign key relationships

    """
    logger.debug(f"GetTableRelationships called for {table_name}")

    # Parse schema.table format
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        schema = "dbo"
        table = table_name

    def _query() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()

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
            return outgoing, incoming
        finally:
            conn.close()

    outgoing, incoming = await run_in_thread(_query)

    result = {
        "table": f"{schema}.{table}",
        "outgoing_relationships": outgoing,
        "incoming_relationships": incoming,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
    }

    logger.debug(
        f"Found {len(outgoing)} outgoing, {len(incoming)} incoming relationships"
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def ListIndexes(table_name: str) -> str:
    """List indexes defined on a table with columns and types.

    Args:
        table_name: Table name (can include schema, e.g., 'dbo.customers')

    Returns:
        JSON string with index definitions including columns and types

    """
    logger.debug(f"ListIndexes called for {table_name}")

    # Parse schema.table format
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        schema = "dbo"
        table = table_name

    def _query() -> list[dict[str, Any]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    i.name AS index_name,
                    i.type_desc AS index_type,
                    i.is_unique,
                    i.is_primary_key,
                    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
                FROM sys.indexes i
                JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE i.object_id = OBJECT_ID(?)
                  AND i.name IS NOT NULL
                GROUP BY i.name, i.type_desc, i.is_unique, i.is_primary_key
                ORDER BY i.is_primary_key DESC, i.name
            """
            cursor.execute(query, (f"{schema}.{table}",))

            indexes = []
            for row in cursor.fetchall():
                indexes.append(
                    {
                        "name": row.index_name,
                        "type": row.index_type,
                        "is_unique": bool(row.is_unique),
                        "is_primary_key": bool(row.is_primary_key),
                        "columns": row.columns,
                    }
                )
            return indexes
        finally:
            conn.close()

    indexes = await run_in_thread(_query)

    result = {
        "table": f"{schema}.{table}",
        "index_count": len(indexes),
        "indexes": indexes,
    }

    logger.debug(f"Found {len(indexes)} indexes for {table_name}")
    return json.dumps(result, indent=2)


@mcp.tool()
async def ListConstraints(table_name: str) -> str:
    """List constraints defined on a table (CHECK, UNIQUE, DEFAULT).

    Args:
        table_name: Table name (can include schema, e.g., 'dbo.orders')

    Returns:
        JSON string with constraint definitions

    """
    logger.debug(f"ListConstraints called for {table_name}")

    # Parse schema.table format
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        schema = "dbo"
        table = table_name

    def _query() -> list[dict[str, Any]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()

            # Query for CHECK and UNIQUE constraints
            constraints_query = """
                SELECT
                    tc.CONSTRAINT_NAME,
                    tc.CONSTRAINT_TYPE,
                    COALESCE(ccu.COLUMN_NAME, '') AS COLUMN_NAME,
                    COALESCE(cc.CHECK_CLAUSE, '') AS CHECK_CLAUSE
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                LEFT JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
                    ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
                    AND tc.TABLE_SCHEMA = ccu.TABLE_SCHEMA
                    AND tc.TABLE_NAME = ccu.TABLE_NAME
                LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
                    ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
                WHERE tc.TABLE_SCHEMA = ?
                  AND tc.TABLE_NAME = ?
                  AND tc.CONSTRAINT_TYPE IN ('CHECK', 'UNIQUE')
                ORDER BY tc.CONSTRAINT_TYPE, tc.CONSTRAINT_NAME
            """
            cursor.execute(constraints_query, (schema, table))

            constraints = []
            for row in cursor.fetchall():
                constraint: dict[str, Any] = {
                    "name": row.CONSTRAINT_NAME,
                    "type": row.CONSTRAINT_TYPE,
                }
                if row.COLUMN_NAME:
                    constraint["column"] = row.COLUMN_NAME
                if row.CHECK_CLAUSE:
                    constraint["definition"] = row.CHECK_CLAUSE

                constraints.append(constraint)

            # Query for DEFAULT constraints
            default_query = """
                SELECT
                    dc.name AS constraint_name,
                    c.name AS column_name,
                    dc.definition AS default_value
                FROM sys.default_constraints dc
                JOIN sys.columns c ON dc.parent_object_id = c.object_id
                    AND dc.parent_column_id = c.column_id
                WHERE OBJECT_SCHEMA_NAME(dc.parent_object_id) = ?
                  AND OBJECT_NAME(dc.parent_object_id) = ?
                ORDER BY c.name
            """
            cursor.execute(default_query, (schema, table))

            for row in cursor.fetchall():
                constraints.append(
                    {
                        "name": row.constraint_name,
                        "type": "DEFAULT",
                        "column": row.column_name,
                        "definition": row.default_value,
                    }
                )

            return constraints
        finally:
            conn.close()

    constraints = await run_in_thread(_query)

    result = {
        "table": f"{schema}.{table}",
        "constraint_count": len(constraints),
        "constraints": constraints,
    }

    logger.debug(f"Found {len(constraints)} constraints for {table_name}")
    return json.dumps(result, indent=2)


@mcp.tool()
async def ListStoredProcedures(schema_filter: str | None = None) -> str:
    """List stored procedures in the database with parameter information.

    Args:
        schema_filter: Optional schema to filter (e.g., 'dbo')

    Returns:
        JSON string with stored procedure names and parameter info

    """
    logger.debug(f"ListStoredProcedures called with schema_filter={schema_filter}")

    def _query() -> list[dict[str, Any]]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    SCHEMA_NAME(p.schema_id) AS schema_name,
                    p.name AS procedure_name,
                    p.create_date,
                    p.modify_date,
                    STUFF((
                        SELECT ', ' + par.name + ' ' + TYPE_NAME(par.user_type_id)
                        FROM sys.parameters par
                        WHERE par.object_id = p.object_id
                        ORDER BY par.parameter_id
                        FOR XML PATH('')
                    ), 1, 2, '') AS parameters
                FROM sys.procedures p
                WHERE SCHEMA_NAME(p.schema_id) = COALESCE(?, SCHEMA_NAME(p.schema_id))
                ORDER BY schema_name, procedure_name
            """
            if schema_filter:
                cursor.execute(query, (schema_filter,))
            else:
                cursor.execute(query, (None,))

            procedures = []
            for row in cursor.fetchall():
                proc: dict[str, Any] = {
                    "schema": row.schema_name,
                    "name": row.procedure_name,
                    "full_name": f"{row.schema_name}.{row.procedure_name}",
                }
                if row.parameters:
                    proc["parameters"] = row.parameters
                else:
                    proc["parameters"] = None

                procedures.append(proc)

            return procedures
        finally:
            conn.close()

    procedures = await run_in_thread(_query)

    result: dict[str, Any] = {
        "database": MSSQL_DATABASE,
        "server": MSSQL_SERVER,
        "procedure_count": len(procedures),
        "procedures": procedures[:500],
    }

    if schema_filter:
        result["schema_filter"] = schema_filter

    if len(procedures) > 500:
        result["note"] = (
            f"Showing first 500 of {len(procedures)} procedures. "
            "Use schema_filter to narrow results."
        )

    logger.debug(f"Found {len(procedures)} stored procedures")
    return json.dumps(result, indent=2)


# =============================================================================
# MCP Resources
# =============================================================================


@mcp.resource("mssql://tables")
async def list_tables_resource() -> str:
    """Resource listing all tables in the database.

    Returns a newline-separated list of all table names.
    """
    logger.debug("Accessing tables resource")

    def _query() -> list[str]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            return [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" for row in cursor.fetchall()]
        finally:
            conn.close()

    tables = await run_in_thread(_query)
    return "\n".join(tables)


@mcp.resource("mssql://views")
async def list_views_resource() -> str:
    """Resource listing all views in the database.

    Returns a newline-separated list of all view names.
    """
    logger.debug("Accessing views resource")

    def _query() -> list[str]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.VIEWS
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            return [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" for row in cursor.fetchall()]
        finally:
            conn.close()

    views = await run_in_thread(_query)
    return "\n".join(views)


@mcp.resource("mssql://schema/{schema_name}")
async def list_schema_tables_resource(schema_name: str) -> str:
    """Resource listing all tables in a specific schema.

    Args:
        schema_name: The schema to list tables from (e.g., 'dbo')

    Returns a newline-separated list of table names in the schema.

    """
    logger.debug(f"Accessing schema resource for {schema_name}")

    def _query() -> list[str]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ?
                ORDER BY TABLE_NAME
            """,
                (schema_name,),
            )
            return [row.TABLE_NAME for row in cursor.fetchall()]
        finally:
            conn.close()

    tables = await run_in_thread(_query)
    return "\n".join(tables)


@mcp.resource("mssql://table/{table_name}/preview")
async def table_preview_resource(table_name: str) -> str:
    """Resource providing a preview of table data (first 10 rows).

    Args:
        table_name: The table to preview (e.g., 'dbo.customers')

    Returns JSON with column info and sample data.

    """
    logger.debug(f"Accessing table preview for {table_name}")

    # Parse schema.table format
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        schema = "dbo"
        table = table_name

    def _query() -> dict[str, Any]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()

            # Get column info
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """,
                (schema, table),
            )
            columns = [
                {"name": row.COLUMN_NAME, "type": row.DATA_TYPE}
                for row in cursor.fetchall()
            ]

            if not columns:
                return {"error": f"Table '{schema}.{table}' not found"}

            # Get sample data (TOP 10)
            cursor.execute(f"SELECT TOP 10 * FROM [{schema}].[{table}]")  # noqa: S608
            col_names = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                row_dict: dict[str, str | None] = {}
                for col, val in zip(col_names, row, strict=True):
                    if val is None:
                        row_dict[col] = None
                    elif isinstance(val, bytes | bytearray):
                        row_dict[col] = val.hex()
                    else:
                        row_dict[col] = str(val)
                rows.append(row_dict)

            return {
                "table": f"{schema}.{table}",
                "columns": columns,
                "preview_rows": len(rows),
                "data": rows,
            }
        finally:
            conn.close()

    result = await run_in_thread(_query)
    return json.dumps(result, indent=2)


@mcp.resource("mssql://info")
async def database_info_resource() -> str:
    """Resource providing database connection information.

    Returns JSON with server, database, and basic statistics.
    """
    logger.debug("Accessing database info resource")

    def _query() -> dict[str, Any]:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()

            # Get table count
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
            """)
            table_count = cursor.fetchone().cnt

            # Get view count
            cursor.execute("SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.VIEWS")
            view_count = cursor.fetchone().cnt

            # Get schema list
            cursor.execute("""
                SELECT DISTINCT TABLE_SCHEMA
                FROM INFORMATION_SCHEMA.TABLES
                ORDER BY TABLE_SCHEMA
            """)
            schemas = [row.TABLE_SCHEMA for row in cursor.fetchall()]

            return {
                "server": MSSQL_SERVER,
                "database": MSSQL_DATABASE,
                "driver": ODBC_DRIVER,
                "table_count": table_count,
                "view_count": view_count,
                "schemas": schemas,
            }
        finally:
            conn.close()

    result = await run_in_thread(_query)
    return json.dumps(result, indent=2)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
