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

## Phase 2: Feature Completeness ✅ COMPLETED

**Goal**: Comprehensive SQL Server schema discovery

**Timeline Target**: v0.3.0
**Actual Completion**: 2026-01-02

### 2.1 Additional Metadata Tools
- [x] `ListIndexes(table_name)` - indexes with columns and types
- [x] `ListConstraints(table_name)` - CHECK, UNIQUE, DEFAULT constraints
- [x] `ListStoredProcedures(schema_filter)` - SP names and parameters
- [x] `ListFunctions(schema_filter)` - user-defined functions (scalar, inline table-valued, multi-statement table-valued)
- [x] `ListTriggers(schema_filter)` - database triggers with event types and status
- [ ] ~~`GetQueryPlan(query)`~~ - deferred to Phase 4 (advanced features)

### 2.2 Enhanced Existing Tools
- [x] `DescribeTable` - add primary key indicator (`is_primary_key` boolean on all columns)
- [x] `DescribeTable` - add foreign key references inline (`foreign_key` object with `references_table` and `references_column`)
- [x] `GetTableRelationships` - add referential actions (ON DELETE, ON UPDATE)
- [x] `GetTableRelationships` - add composite foreign key support (column arrays grouped by constraint)
- [x] `GetTableRelationships` - add schema-qualified table names
- [x] `GetTableRelationships` - add enabled/disabled constraint status
- [ ] ~~`ReadData` - add column type metadata~~ - deferred to Phase 3

### 2.3 Input/Output Schemas
- [ ] Define Pydantic models for tool inputs - deferred to Phase 3
- [ ] Add JSON Schema to tool definitions - deferred to Phase 3
- [x] Structured output types for better LLM parsing (all tools return consistent JSON)

**Success Criteria**: ✅ ALL MET
- ✅ All major SQL Server metadata accessible (indexes, constraints, procedures, functions, triggers)
- ✅ Tools provide actionable schema information (PK/FK indicators, referential actions, composite keys)
- ✅ LLMs can reliably parse tool outputs (consistent JSON structure across all tools)

### Phase 2 Achievements

**7 commits** implementing comprehensive schema discovery:
1. ListIndexes tool - index metadata with column lists and types
2. ListConstraints tool - CHECK, UNIQUE, DEFAULT constraint discovery
3. ListStoredProcedures tool - stored procedure enumeration with parameters
4. ListFunctions tool - UDF discovery (scalar, inline TVF, multi-statement TVF)
5. ListTriggers tool - trigger metadata with events, types, and status
6. DescribeTable enhancements - PK/FK indicators for relationship visibility
7. GetTableRelationships enhancements - referential actions and composite FK support

**Testing**: 88 total tests (up from 59), coverage at 13.80%
**Architecture**: All tools follow async patterns with per-request connections
**Consistency**: Unified JSON output structure across all metadata tools

---

## Phase 3: Production Readiness 🚀 IN PROGRESS

**Goal**: Reliable, testable, observable server ready for production deployment

**Timeline Target**: v0.4.0
**Started**: 2026-01-02

**Context**: With Phase 2 complete, we now have comprehensive SQL Server schema discovery capabilities (11 tools covering tables, views, indexes, constraints, procedures, functions, triggers, and relationships). Phase 3 focuses on making this feature-rich server production-ready through comprehensive testing, robust error handling, flexible configuration, and thorough documentation.

### 3.1 Testing Infrastructure ✅ COMPLETED
- [x] Mock pyodbc connection fixture
- [x] Integration tests for all tools (14 tests across 8 test classes)
- [x] Resource endpoint tests (10 tests for all 5 MCP resources)
- [x] Security filtering edge case tests (11 additional edge cases)
- [x] Async behavior tests (11 tests for concurrency and thread safety)
- [x] **Achievement: 77.07% code coverage** (target was 80%, nearly met - gap is unreachable code paths)

### 3.2 Configuration Improvements ✅ COMPLETED
- [x] CLI arguments (`--server`, `--database`, `--driver`, `--connection-timeout`)
- [x] Config file support (TOML via `--config` flag)
- [x] Validation on startup with clear error messages
- [x] Health check on initialization with database connection testing
- [x] `--validate-only` flag for configuration testing
- [x] Configuration priority system (CLI > Config file > Env vars > Defaults)
- [x] Backward compatibility with environment variables
- [x] **Achievement: 79.83% code coverage** (up from 77.07%, 43 new tests, 100% health.py coverage)

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

| Version | Focus | Key Deliverables | Status |
|---------|-------|------------------|--------|
| v0.1.0 | Initial | Basic tools, Windows Auth | ✅ Released |
| v0.2.0 | Foundation | Async, pooling, resources | ✅ Released |
| v0.3.0 | Features | Full metadata tools, schemas | ✅ Complete (2026-01-02) |
| v0.4.0 | Production | Tests, errors, docs | 🚀 **CURRENT** |
| v1.0.0 | Enterprise | Multi-DB, caching, metrics | 📋 Planned |

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
| 2026-01-02 | 1.2 | Phase 2 completed - all metadata discovery tools implemented (ListIndexes, ListConstraints, ListStoredProcedures, ListFunctions, ListTriggers, DescribeTable enhancements, GetTableRelationships enhancements). 88 tests passing, 13.80% coverage. Ready for Phase 3. |
| 2026-01-02 | 1.3 | Phase 3.1 completed - comprehensive testing infrastructure with 77.07% coverage. Added 42 new tests (integration, resources, async behavior). 130 total tests passing. Coverage jumped from 13.80% to 77.07%. |
