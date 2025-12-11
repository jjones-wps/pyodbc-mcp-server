# pyodbc MCP Server Roadmap

This document outlines the development roadmap for transforming the pyodbc MCP Server from a basic tool-only implementation to a production-ready, fully MCP-compliant server.

## Current State (v0.1.0)

- 5 basic tools: `ListTables`, `ListViews`, `DescribeTable`, `GetTableRelationships`, `ReadData`
- Synchronous blocking database calls
- No connection pooling (new connection per call)
- Basic keyword-based SQL security filtering
- Windows Authentication only

## Target State (v1.0.0)

- Full MCP protocol compliance (Tools + Resources)
- Async non-blocking architecture
- Connection pooling with lifespan management
- Comprehensive schema discovery tools
- Structured logging and observability
- Production-ready error handling
- Integration test coverage

---

## Phase 1: Architecture Foundation

**Goal**: Establish async architecture with connection pooling and MCP Resources

**Timeline Target**: v0.2.0

### 1.1 Async Conversion
- [x] Wrap synchronous pyodbc calls with `anyio.to_thread` (used instead of asyncer)
- [x] Convert all tool functions to async
- [x] Add `async` context manager for database operations

### 1.2 Connection Pooling via Lifespan
- [x] Implement FastMCP lifespan context manager
- [x] Create shared connection pool initialized at startup
- [x] Proper cleanup on server shutdown
- [ ] Connection health checking

### 1.3 MCP Resources Implementation
- [x] Add `@mcp.resource("mssql://tables")` - list all tables as resource
- [x] Add `@mcp.resource("mssql://table/{table_name}/preview")` - table preview resource
- [x] Add `@mcp.resource("mssql://schema/{schema_name}")` - schema-filtered tables
- [x] Add `@mcp.resource("mssql://views")` - list all views as resource
- [x] Add `@mcp.resource("mssql://info")` - database server info

### 1.4 Context-Based Logging
- [x] Add Python `logging` module integration (used instead of FastMCP Context)
- [x] Log query execution and operations
- [x] Log connection pool status
- [ ] Log query execution times (TODO: add timing metrics)

**Success Criteria**:
- Server handles concurrent requests without blocking
- Connection reuse verified via logging
- Resources appear in MCP client resource lists

---

## Phase 2: Feature Completeness

**Goal**: Comprehensive SQL Server schema discovery

**Timeline Target**: v0.3.0

### 2.1 Additional Metadata Tools
- [ ] `ListIndexes(table_name)` - indexes with columns and types
- [ ] `ListConstraints(table_name)` - CHECK, UNIQUE, DEFAULT constraints
- [ ] `ListStoredProcedures(schema_filter)` - SP names and parameters
- [ ] `ListFunctions(schema_filter)` - user-defined functions
- [ ] `GetQueryPlan(query)` - estimated execution plan for SELECT

### 2.2 Enhanced Existing Tools
- [ ] `DescribeTable` - add primary key indicator
- [ ] `DescribeTable` - add foreign key references inline
- [ ] `GetTableRelationships` - add relationship cardinality hints
- [ ] `ReadData` - add column type metadata in response

### 2.3 Input/Output Schemas
- [ ] Define Pydantic models for tool inputs
- [ ] Add JSON Schema to tool definitions
- [ ] Structured output types for better LLM parsing

**Success Criteria**:
- All major SQL Server metadata accessible
- Tools provide actionable schema information
- LLMs can reliably parse tool outputs

---

## Phase 3: Production Readiness

**Goal**: Reliable, testable, observable server

**Timeline Target**: v0.4.0

### 3.1 Testing Infrastructure
- [ ] Mock pyodbc connection fixture
- [ ] Integration tests for all tools
- [ ] Resource endpoint tests
- [ ] Security filtering edge case tests
- [ ] Async behavior tests
- [ ] Target: 80%+ code coverage

### 3.2 Configuration Improvements
- [ ] CLI arguments (`--server`, `--database`, `--driver`)
- [ ] Config file support (TOML/YAML)
- [ ] Validation on startup with clear error messages
- [ ] Health check on initialization

### 3.3 Error Handling
- [ ] Typed error classes (ConnectionError, QueryError, SecurityError)
- [ ] Consistent error response format
- [ ] Query timeout handling (configurable)
- [ ] Retry logic for transient failures

### 3.4 Documentation
- [ ] API documentation for all tools
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Example queries and use cases

**Success Criteria**:
- All tests pass in CI
- Clear error messages for common failure modes
- Documentation covers all features

---

## Phase 4: Advanced Features

**Goal**: Enterprise-ready capabilities

**Timeline Target**: v1.0.0

### 4.1 Multi-Database Support
- [ ] `SwitchDatabase(database_name)` tool
- [ ] `ListDatabases()` tool
- [ ] Per-request database context

### 4.2 Performance Features
- [ ] Query result caching with TTL
- [ ] Prepared statement caching
- [ ] Query complexity analysis (block expensive queries)

### 4.3 Observability
- [ ] Metrics endpoint (query count, latency, errors)
- [ ] Resource change notifications
- [ ] Audit logging for queries

### 4.4 Extended Query Support
- [ ] Stored procedure execution (read-only, returns results)
- [ ] Table-valued function calls
- [ ] Parameterized query templates

**Success Criteria**:
- Production deployment validated
- Performance benchmarks documented
- Enterprise security requirements met

---

## Version Milestones

| Version | Focus | Key Deliverables |
|---------|-------|------------------|
| v0.1.0 | Initial | Basic tools, Windows Auth |
| v0.2.0 | Foundation | Async, pooling, resources (CURRENT) |
| v0.3.0 | Features | Full metadata tools, schemas |
| v0.4.0 | Production | Tests, errors, docs |
| v1.0.0 | Enterprise | Multi-DB, caching, metrics |

---

## Non-Goals

These are explicitly out of scope:

- **Write operations**: Server remains read-only by design
- **SQL Server authentication**: Windows Auth only (security policy)
- **Cross-platform**: Windows-only (matches use case)
- **Connection string storage**: Credentials via env vars only
- **Query builder UI**: This is an MCP server, not an application

---

## Dependencies

| Dependency | Current | Target | Notes |
|------------|---------|--------|-------|
| fastmcp | >=0.1.0 | latest | Core MCP framework |
| pyodbc | >=5.0.0 | >=5.0.0 | SQL Server connectivity |
| asyncer | - | >=0.0.2 | Async wrapper for sync code |
| pydantic | - | >=2.0.0 | Input validation |

---

## How to Contribute

1. Pick an unchecked item from any phase
2. Create a feature branch: `feature/phase-X-description`
3. Implement with tests
4. Update CHANGELOG.md
5. Submit PR referencing this roadmap

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-11 | 1.0 | Initial roadmap created |
| 2024-12-11 | 1.1 | Phase 1 completed - async, pooling, resources implemented |
