# Architecture Documentation

This document describes the current architecture and the target architecture for the MSSQL MCP Server.

## Current Architecture (v0.1.0)

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client                              │
│              (Claude Code / Claude Desktop)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ stdio (JSON-RPC)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastMCP Server                            │
│                   (mssql-readonly)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Tool Layer                          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
│  │  │ ListTables  │ │ ListViews   │ │ DescribeTable   │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘  │  │
│  │  ┌─────────────────────┐ ┌─────────────────────────┐  │  │
│  │  │ GetTableRelations   │ │      ReadData           │  │  │
│  │  └─────────────────────┘ └─────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌───────────────────────────▼───────────────────────────┐  │
│  │              Connection Function                       │  │
│  │         get_connection() → pyodbc.Connection          │  │
│  │         (Creates new connection per call)              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ ODBC (TDS Protocol)
                          │ Windows Authentication
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQL Server Database                        │
│              (INFORMATION_SCHEMA, sys.*)                     │
└─────────────────────────────────────────────────────────────┘
```

### Current Flow

1. MCP client sends tool call via stdio
2. FastMCP routes to appropriate tool function
3. Tool creates NEW database connection
4. Tool executes query synchronously (BLOCKS)
5. Tool closes connection
6. Tool returns JSON string result

### Current Issues

| Issue | Impact | Severity |
|-------|--------|----------|
| Synchronous pyodbc calls | Blocks event loop during query | High |
| No connection pooling | Latency on every call, connection overhead | High |
| No MCP Resources | Missing protocol feature, limited discovery | Medium |
| No structured logging | Difficult to debug issues | Medium |
| Basic error handling | Generic error messages | Low |

---

## Target Architecture (v1.0.0)

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client                              │
│              (Claude Code / Claude Desktop)                  │
└──────────────┬──────────────────────────┬───────────────────┘
               │ Tools                     │ Resources
               ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastMCP Server                            │
│                   (mssql-readonly)                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Lifespan Manager                       ││
│  │  • Initialize connection pool on startup                 ││
│  │  • Health check connections                              ││
│  │  • Cleanup on shutdown                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                               │
│  ┌───────────────────────────▼───────────────────────────┐  │
│  │                  Context Layer                         │  │
│  │  • Shared connection pool (ctx.lifespan_context)       │  │
│  │  • Logging (ctx.info, ctx.debug, ctx.error)           │  │
│  │  • Request tracking (ctx.request_id)                   │  │
│  └───────────────────────────────────────────────────────┘  │
│           │                                    │             │
│  ┌────────▼────────┐              ┌───────────▼──────────┐  │
│  │   Tool Layer    │              │   Resource Layer      │  │
│  │                 │              │                       │  │
│  │  Schema Tools:  │              │  mssql://tables       │  │
│  │  • ListTables   │              │  mssql://{s}/{t}      │  │
│  │  • ListViews    │              │  mssql://schema/{s}   │  │
│  │  • ListIndexes  │              │                       │  │
│  │  • ListSPs      │              │  Returns:             │  │
│  │  • Describe*    │              │  • Table lists        │  │
│  │                 │              │  • Data previews      │  │
│  │  Query Tools:   │              │  • Schema info        │  │
│  │  • ReadData     │              │                       │  │
│  │  • QueryPlan    │              │                       │  │
│  └─────────────────┘              └───────────────────────┘  │
│           │                                    │             │
│  ┌────────▼────────────────────────────────────▼──────────┐ │
│  │              Async Database Layer                       │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │           Connection Pool                        │   │ │
│  │  │  • Pre-initialized connections                   │   │ │
│  │  │  • Automatic reconnection                        │   │ │
│  │  │  • Health monitoring                             │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  │                         │                               │ │
│  │  ┌──────────────────────▼──────────────────────────┐   │ │
│  │  │        Async Query Executor                      │   │ │
│  │  │  • asyncer.asyncify() wrapper                    │   │ │
│  │  │  • Query timeout handling                        │   │ │
│  │  │  • Result streaming for large sets               │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  │                         │                               │ │
│  │  ┌──────────────────────▼──────────────────────────┐   │ │
│  │  │         Security Layer                           │   │ │
│  │  │  • Query validation (SELECT only)                │   │ │
│  │  │  • Keyword blocking                              │   │ │
│  │  │  • Row limiting                                  │   │ │
│  │  │  • Query complexity checks                       │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          │ ODBC (Pooled Connections)
                          │ Windows Authentication
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQL Server Database                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### Lifespan Manager

```python
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize and cleanup server resources."""
    # Startup
    pool = ConnectionPool(
        server=MSSQL_SERVER,
        database=MSSQL_DATABASE,
        driver=ODBC_DRIVER,
        pool_size=5,
        max_overflow=10
    )
    await pool.initialize()

    try:
        yield {"pool": pool}
    finally:
        # Shutdown
        await pool.close()
```

### Connection Pool

```python
class ConnectionPool:
    """Manages reusable database connections."""

    def __init__(self, server, database, driver, pool_size=5):
        self.conn_str = self._build_conn_str(server, database, driver)
        self.pool_size = pool_size
        self._connections: Queue[Connection] = Queue()
        self._lock = asyncio.Lock()

    async def acquire(self) -> Connection:
        """Get a connection from the pool."""
        ...

    async def release(self, conn: Connection):
        """Return a connection to the pool."""
        ...

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Context manager for automatic acquire/release."""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)
```

### Async Query Executor

```python
import asyncer

async def execute_query(pool: ConnectionPool, query: str, params=None) -> list[dict]:
    """Execute query asynchronously without blocking."""
    async with pool.connection() as conn:
        # Run blocking pyodbc in thread pool
        def _execute():
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

        return await asyncer.asyncify(_execute)()
```

### Resource Definitions

```python
@mcp.resource("mssql://tables")
async def list_all_tables() -> str:
    """List all tables as a browsable resource."""
    ...

@mcp.resource("mssql://{schema}/{table}")
async def table_preview(schema: str, table: str) -> str:
    """Preview first 10 rows of a table."""
    ...

@mcp.resource("mssql://schema/{schema}")
async def schema_tables(schema: str) -> str:
    """List tables in a specific schema."""
    ...
```

---

## Data Flow

### Tool Call Flow (Target)

```
1. Client sends tools/call request
2. FastMCP validates input against schema
3. Tool function receives Context with pool
4. Tool logs operation start: ctx.info("Listing tables...")
5. Tool acquires connection from pool (non-blocking)
6. Tool executes query via async executor
7. Tool releases connection to pool
8. Tool logs completion with timing
9. Tool returns structured JSON response
10. FastMCP sends response to client
```

### Resource Read Flow (Target)

```
1. Client sends resources/read request
2. FastMCP matches URI pattern
3. Resource function extracts parameters
4. Resource executes query via shared pool
5. Resource returns formatted data
6. FastMCP sends response to client
```

---

## File Structure (Target)

```
src/mssql_mcp_server/
├── __init__.py
├── __main__.py
├── server.py              # FastMCP server setup, lifespan
├── tools/
│   ├── __init__.py
│   ├── schema.py          # ListTables, ListViews, DescribeTable, etc.
│   ├── query.py           # ReadData, GetQueryPlan
│   └── relationships.py   # GetTableRelationships
├── resources/
│   ├── __init__.py
│   └── tables.py          # Table resources
├── database/
│   ├── __init__.py
│   ├── pool.py            # Connection pool implementation
│   ├── executor.py        # Async query execution
│   └── security.py        # Query validation
├── models/
│   ├── __init__.py
│   └── schemas.py         # Pydantic models for inputs/outputs
└── config.py              # Configuration management
```

---

## Migration Path

### Phase 1: Minimal Disruption
1. Add lifespan without changing tools (backward compatible)
2. Add Context parameter as optional
3. Add resources alongside existing tools

### Phase 2: Async Conversion
1. Create async wrappers for existing sync functions
2. Migrate tools one at a time
3. Keep sync versions as fallback

### Phase 3: Refactoring
1. Extract tools into separate modules
2. Add Pydantic schemas
3. Improve error handling

### Phase 4: Optimization
1. Add caching layer
2. Add metrics
3. Performance tuning

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Transport Security                                  │
│ • stdio only (no network exposure)                          │
│ • MCP client authentication handled by host                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Authentication                                      │
│ • Windows Authentication (Trusted_Connection=yes)           │
│ • No credentials stored in server                           │
│ • Leverages domain security                                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Authorization                                       │
│ • SQL Server permissions (SELECT only granted)              │
│ • Query filtering (SELECT prefix required)                  │
│ • Keyword blocking (INSERT, UPDATE, DELETE, etc.)           │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Resource Protection                                 │
│ • Row limiting (max 1000 per query)                         │
│ • Query timeout (configurable)                              │
│ • Result size limiting                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-12-11 | 1.0 | Claude Code | Initial architecture document |
