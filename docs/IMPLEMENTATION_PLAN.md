# Implementation Plan

Detailed technical specifications for implementing the MSSQL MCP Server roadmap.

---

## Phase 1: Architecture Foundation

### Task 1.1: Add Lifespan Manager

**File**: `src/mssql_mcp_server/server.py`

**Changes**:
```python
# Add imports
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any

# Add lifespan function
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Initialize server resources on startup, cleanup on shutdown."""
    # Create a single connection for now (pool in next task)
    conn = get_connection()
    try:
        yield {"db": conn}
    finally:
        conn.close()

# Update FastMCP initialization
mcp = FastMCP("mssql-readonly", lifespan=server_lifespan)
```

**Testing**:
```python
def test_lifespan_initializes_connection():
    """Verify lifespan creates and yields connection."""
    ...

def test_lifespan_closes_connection_on_shutdown():
    """Verify connection is closed in finally block."""
    ...
```

**Acceptance Criteria**:
- [ ] Server starts without errors
- [ ] Connection created once at startup
- [ ] Connection closed on shutdown
- [ ] Existing tools continue to work

---

### Task 1.2: Add Connection Pool

**New File**: `src/mssql_mcp_server/database/pool.py`

**Implementation**:
```python
"""Connection pool for database connections."""

import asyncio
from queue import Queue
from typing import Optional
import pyodbc

class ConnectionPool:
    """Simple connection pool for pyodbc connections."""

    def __init__(
        self,
        conn_str: str,
        pool_size: int = 5,
        max_overflow: int = 5
    ):
        self.conn_str = conn_str
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: Queue[pyodbc.Connection] = Queue(maxsize=pool_size)
        self._overflow_count = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Pre-create connections for the pool."""
        for _ in range(self.pool_size):
            conn = pyodbc.connect(self.conn_str, timeout=30)
            self._pool.put(conn)
        self._initialized = True

    async def acquire(self) -> pyodbc.Connection:
        """Get a connection from the pool."""
        if not self._initialized:
            raise RuntimeError("Pool not initialized")

        try:
            return self._pool.get_nowait()
        except:
            async with self._lock:
                if self._overflow_count < self.max_overflow:
                    self._overflow_count += 1
                    return pyodbc.connect(self.conn_str, timeout=30)
            # Wait for available connection
            return self._pool.get(timeout=30)

    async def release(self, conn: pyodbc.Connection) -> None:
        """Return a connection to the pool."""
        try:
            # Test connection is still valid
            conn.cursor().execute("SELECT 1")
            self._pool.put_nowait(conn)
        except:
            # Connection is dead, close it
            try:
                conn.close()
            except:
                pass
            # Create replacement if under pool_size
            if self._pool.qsize() < self.pool_size:
                new_conn = pyodbc.connect(self.conn_str, timeout=30)
                self._pool.put(new_conn)

    async def close(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass

    @property
    def available(self) -> int:
        """Number of available connections."""
        return self._pool.qsize()
```

**Update lifespan**:
```python
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )
    pool = ConnectionPool(conn_str, pool_size=3)
    await pool.initialize()
    try:
        yield {"pool": pool}
    finally:
        await pool.close()
```

**Acceptance Criteria**:
- [ ] Pool initializes with configured number of connections
- [ ] Connections are reused across tool calls
- [ ] Pool handles connection failures gracefully
- [ ] Pool closes all connections on shutdown

---

### Task 1.3: Add Async Query Execution

**New File**: `src/mssql_mcp_server/database/executor.py`

**Dependencies**: Add `asyncer>=0.0.2` to pyproject.toml

**Implementation**:
```python
"""Async query execution utilities."""

from typing import Any, Optional
import asyncer
import pyodbc

async def execute_query(
    conn: pyodbc.Connection,
    query: str,
    params: Optional[tuple] = None,
    max_rows: int = 100
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Execute a query asynchronously.

    Returns:
        Tuple of (column_names, rows_as_dicts)
    """
    def _execute() -> tuple[list[str], list[dict[str, Any]]]:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        rows = []
        for i, row in enumerate(cursor):
            if i >= max_rows:
                break
            row_dict = {}
            for col, val in zip(columns, row):
                if val is None:
                    row_dict[col] = None
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[col] = val.hex()
                else:
                    row_dict[col] = str(val)
            rows.append(row_dict)

        return columns, rows

    return await asyncer.asyncify(_execute)()


async def execute_scalar(
    conn: pyodbc.Connection,
    query: str,
    params: Optional[tuple] = None
) -> Any:
    """Execute a query and return single value."""
    def _execute() -> Any:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row else None

    return await asyncer.asyncify(_execute)()
```

**Acceptance Criteria**:
- [ ] Queries execute without blocking event loop
- [ ] Results are properly serialized to JSON-safe types
- [ ] Row limiting is respected
- [ ] Parameters are properly bound

---

### Task 1.4: Convert Tools to Async with Context

**File**: `src/mssql_mcp_server/server.py`

**Pattern for each tool**:
```python
from fastmcp import Context

@mcp.tool()
async def ListTables(
    schema_filter: Optional[str] = None,
    ctx: Context = None
) -> str:
    """Lists all tables in the SQL Server database."""

    # Get pool from lifespan context
    pool = ctx.request_context.lifespan_context["pool"]

    # Log operation
    if ctx:
        await ctx.info(f"Listing tables (filter: {schema_filter})")

    # Acquire connection and execute
    conn = await pool.acquire()
    try:
        query = """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """
        params = None
        if schema_filter:
            query += " AND TABLE_SCHEMA = ?"
            params = (schema_filter,)
        else:
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"

        columns, rows = await execute_query(conn, query, params, max_rows=500)

        tables = [f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}" for r in rows]

        result = {
            "database": MSSQL_DATABASE,
            "server": MSSQL_SERVER,
            "table_count": len(tables),
            "tables": tables
        }

        if len(tables) >= 500:
            result["note"] = "Results limited to 500. Use schema_filter."

        return json.dumps(result, indent=2)
    finally:
        await pool.release(conn)
```

**Acceptance Criteria**:
- [ ] All 5 tools converted to async
- [ ] All tools use connection pool
- [ ] All tools log via Context
- [ ] Backward compatibility maintained (tools still work)

---

### Task 1.5: Add MCP Resources

**File**: `src/mssql_mcp_server/server.py` (or new `resources.py`)

**Implementation**:
```python
@mcp.resource("mssql://tables")
async def resource_all_tables(ctx: Context) -> str:
    """
    List all tables in the database as a browsable resource.

    URI: mssql://tables
    """
    # Reuse ListTables logic
    return await ListTables(ctx=ctx)


@mcp.resource("mssql://tables/{schema}")
async def resource_schema_tables(schema: str, ctx: Context) -> str:
    """
    List tables in a specific schema.

    URI: mssql://tables/dbo
    """
    return await ListTables(schema_filter=schema, ctx=ctx)


@mcp.resource("mssql://table/{schema}/{table}")
async def resource_table_preview(schema: str, table: str, ctx: Context) -> str:
    """
    Preview first 10 rows of a table.

    URI: mssql://table/dbo/customers
    """
    # Security: validate table name format
    if not schema.isidentifier() or not table.replace('_', '').isalnum():
        return json.dumps({"error": "Invalid schema or table name"})

    query = f"SELECT TOP 10 * FROM [{schema}].[{table}]"
    return await ReadData(query=query, max_rows=10, ctx=ctx)


@mcp.resource("mssql://schema/{schema}/{table}")
async def resource_table_schema(schema: str, table: str, ctx: Context) -> str:
    """
    Get column definitions for a table.

    URI: mssql://schema/dbo/customers
    """
    return await DescribeTable(table_name=f"{schema}.{table}", ctx=ctx)
```

**Acceptance Criteria**:
- [ ] Resources appear in `resources/list` response
- [ ] Resources can be read via `resources/read`
- [ ] Resources return valid JSON
- [ ] URI parameters are properly extracted

---

### Task 1.6: Add Structured Logging

**Updates across all tools**:
```python
@mcp.tool()
async def ReadData(query: str, max_rows: int = 100, ctx: Context = None) -> str:
    """Execute a SELECT query with security filtering."""

    start_time = time.time()

    if ctx:
        await ctx.debug(f"ReadData called with max_rows={max_rows}")

    # Security validation
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        if ctx:
            await ctx.warning(f"Blocked non-SELECT query attempt")
        return json.dumps({"error": "Only SELECT queries allowed"})

    # Check dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        if f" {keyword} " in f" {query_upper} ":
            if ctx:
                await ctx.warning(f"Blocked query with keyword: {keyword}")
            return json.dumps({"error": f"Forbidden keyword: {keyword}"})

    # Execute query
    pool = ctx.request_context.lifespan_context["pool"]
    conn = await pool.acquire()
    try:
        columns, rows = await execute_query(conn, query, max_rows=max_rows)

        elapsed = time.time() - start_time
        if ctx:
            await ctx.info(f"Query returned {len(rows)} rows in {elapsed:.2f}s")

        return json.dumps({
            "columns": columns,
            "row_count": len(rows),
            "max_rows": max_rows,
            "data": rows
        }, indent=2)

    except pyodbc.Error as e:
        if ctx:
            await ctx.error(f"Database error: {str(e)}")
        return json.dumps({"error": f"Database error: {str(e)}"})

    finally:
        await pool.release(conn)
```

**Acceptance Criteria**:
- [ ] All tools log at appropriate levels
- [ ] Query timing is logged
- [ ] Security violations are logged as warnings
- [ ] Errors are logged with details

---

## Phase 2: Feature Completeness

### Task 2.1: ListIndexes Tool

```python
@mcp.tool()
async def ListIndexes(table_name: str, ctx: Context = None) -> str:
    """
    Get indexes defined on a table.

    Args:
        table_name: Table name (can include schema, e.g., 'dbo.customers')

    Returns:
        JSON with index definitions including columns and types
    """
    schema, table = parse_table_name(table_name)

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

    pool = ctx.request_context.lifespan_context["pool"]
    conn = await pool.acquire()
    try:
        columns, rows = await execute_query(conn, query, (f"{schema}.{table}",))

        indexes = [
            {
                "name": r["index_name"],
                "type": r["index_type"],
                "is_unique": r["is_unique"] == "1",
                "is_primary_key": r["is_primary_key"] == "1",
                "columns": r["columns"]
            }
            for r in rows
        ]

        return json.dumps({
            "table": f"{schema}.{table}",
            "index_count": len(indexes),
            "indexes": indexes
        }, indent=2)

    finally:
        await pool.release(conn)
```

---

### Task 2.2: ListConstraints Tool

```python
@mcp.tool()
async def ListConstraints(table_name: str, ctx: Context = None) -> str:
    """
    Get constraints defined on a table (CHECK, DEFAULT, UNIQUE).

    Args:
        table_name: Table name (can include schema)

    Returns:
        JSON with constraint definitions
    """
    schema, table = parse_table_name(table_name)

    query = """
        SELECT
            cc.CONSTRAINT_NAME,
            cc.CONSTRAINT_TYPE,
            ccu.COLUMN_NAME,
            cc.CHECK_CLAUSE
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        LEFT JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
            ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
            ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ?
        ORDER BY tc.CONSTRAINT_TYPE, tc.CONSTRAINT_NAME
    """
    # Implementation continues...
```

---

### Task 2.3: ListStoredProcedures Tool

```python
@mcp.tool()
async def ListStoredProcedures(schema_filter: Optional[str] = None, ctx: Context = None) -> str:
    """
    List stored procedures in the database.

    Args:
        schema_filter: Optional schema to filter (e.g., 'dbo')

    Returns:
        JSON with stored procedure names and parameter info
    """
    query = """
        SELECT
            SCHEMA_NAME(p.schema_id) AS schema_name,
            p.name AS procedure_name,
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
    # Implementation continues...
```

---

### Task 2.4: GetQueryPlan Tool

```python
@mcp.tool()
async def GetQueryPlan(query: str, ctx: Context = None) -> str:
    """
    Get the estimated execution plan for a SELECT query.

    Args:
        query: SELECT query to analyze

    Returns:
        JSON with execution plan summary
    """
    # Security: must be SELECT
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries allowed"})

    # Enable showplan
    plan_query = f"""
        SET SHOWPLAN_TEXT ON;
        GO
        {query}
        GO
        SET SHOWPLAN_TEXT OFF;
    """
    # Note: This requires special handling...
```

---

## Phase 3: Testing Infrastructure

### Task 3.1: Mock Database Fixture

**New File**: `tests/conftest.py`

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_connection():
    """Create a mock pyodbc connection."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def mock_pool(mock_connection):
    """Create a mock connection pool."""
    conn, cursor = mock_connection
    pool = AsyncMock()
    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock()
    return pool


@pytest.fixture
def mock_context(mock_pool):
    """Create a mock FastMCP context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"pool": mock_pool}
    ctx.info = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx
```

### Task 3.2: Integration Tests

**File**: `tests/test_tools_integration.py`

```python
import pytest
from mssql_mcp_server.server import ListTables, ReadData

@pytest.mark.asyncio
async def test_list_tables_returns_tables(mock_context, mock_connection):
    """ListTables should return table list."""
    conn, cursor = mock_connection
    cursor.fetchall.return_value = [
        MagicMock(TABLE_SCHEMA='dbo', TABLE_NAME='users'),
        MagicMock(TABLE_SCHEMA='dbo', TABLE_NAME='orders'),
    ]
    cursor.description = [('TABLE_SCHEMA',), ('TABLE_NAME',)]

    result = await ListTables(ctx=mock_context)
    data = json.loads(result)

    assert data['table_count'] == 2
    assert 'dbo.users' in data['tables']


@pytest.mark.asyncio
async def test_read_data_blocks_insert(mock_context):
    """ReadData should reject INSERT queries."""
    result = await ReadData(query="INSERT INTO users VALUES (1)", ctx=mock_context)
    data = json.loads(result)

    assert 'error' in data
    assert 'SELECT' in data['error']


@pytest.mark.asyncio
async def test_read_data_blocks_delete_in_subquery(mock_context):
    """ReadData should reject DELETE even in subqueries."""
    result = await ReadData(
        query="SELECT * FROM (DELETE FROM users) AS t",
        ctx=mock_context
    )
    data = json.loads(result)

    assert 'error' in data
    assert 'DELETE' in data['error']
```

---

## Dependency Updates

**pyproject.toml additions**:
```toml
dependencies = [
    "fastmcp>=0.1.0",
    "pyodbc>=5.0.0",
    "asyncer>=0.0.2",      # NEW: async wrapper
    "pydantic>=2.0.0",     # NEW: input validation
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",  # NEW: async test support
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
]
```

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-11 | 1.0 | Initial implementation plan |
