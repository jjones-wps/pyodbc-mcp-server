# GitHub Issues Guide

This document provides issue templates and a tracking structure for the MSSQL MCP Server roadmap.

---

## Issue Labels

### Priority Labels
- `priority: critical` - Blocking issue, needs immediate attention
- `priority: high` - Important for next release
- `priority: medium` - Should be done, but not urgent
- `priority: low` - Nice to have

### Type Labels
- `type: feature` - New functionality
- `type: bug` - Something isn't working
- `type: refactor` - Code improvement without functional change
- `type: docs` - Documentation only
- `type: test` - Test coverage improvement

### Phase Labels
- `phase: 1-foundation` - Architecture foundation work
- `phase: 2-features` - Feature completeness
- `phase: 3-production` - Production readiness
- `phase: 4-advanced` - Advanced features

### Component Labels
- `component: tools` - MCP tool functions
- `component: resources` - MCP resource functions
- `component: database` - Connection pool, executor
- `component: security` - Query filtering, validation
- `component: tests` - Test infrastructure

---

## Phase 1 Issues (Foundation)

### Issue #1: Add FastMCP Lifespan Manager

**Title**: feat: Add lifespan manager for server initialization

**Labels**: `type: feature`, `phase: 1-foundation`, `component: database`, `priority: high`

**Description**:
```markdown
## Summary
Implement FastMCP lifespan context manager to handle server startup and shutdown.

## Requirements
- [ ] Create `server_lifespan()` async context manager
- [ ] Initialize database connection on startup
- [ ] Clean up connection on shutdown
- [ ] Pass connection via lifespan context

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.1

## Acceptance Criteria
- Server starts without errors
- Connection created once at startup
- Connection closed on shutdown
- Existing tools continue to work
```

---

### Issue #2: Implement Connection Pool

**Title**: feat: Add connection pooling for database connections

**Labels**: `type: feature`, `phase: 1-foundation`, `component: database`, `priority: high`

**Description**:
```markdown
## Summary
Create a connection pool to reuse database connections across tool calls.

## Requirements
- [ ] Create `ConnectionPool` class in `src/mssql_mcp_server/database/pool.py`
- [ ] Support configurable pool size
- [ ] Handle connection failures gracefully
- [ ] Integrate with lifespan manager

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.2

## Acceptance Criteria
- Pool initializes with configured number of connections
- Connections are reused across tool calls
- Pool handles connection failures gracefully
- Pool closes all connections on shutdown
```

---

### Issue #3: Add Async Query Execution

**Title**: feat: Add async wrapper for pyodbc queries

**Labels**: `type: feature`, `phase: 1-foundation`, `component: database`, `priority: high`

**Description**:
```markdown
## Summary
Wrap synchronous pyodbc calls to run asynchronously without blocking the event loop.

## Requirements
- [ ] Add `asyncer` dependency to pyproject.toml
- [ ] Create `execute_query()` async function
- [ ] Create `execute_scalar()` async function
- [ ] Ensure proper JSON serialization of results

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.3

## Acceptance Criteria
- Queries execute without blocking event loop
- Results are properly serialized to JSON-safe types
- Row limiting is respected
- Parameters are properly bound
```

---

### Issue #4: Convert Tools to Async

**Title**: refactor: Convert all tools to async with Context

**Labels**: `type: refactor`, `phase: 1-foundation`, `component: tools`, `priority: high`

**Description**:
```markdown
## Summary
Convert all 5 existing tools to async functions that use the connection pool.

## Requirements
- [ ] Add `Context` parameter to all tools
- [ ] Convert `ListTables` to async
- [ ] Convert `ListViews` to async
- [ ] Convert `DescribeTable` to async
- [ ] Convert `GetTableRelationships` to async
- [ ] Convert `ReadData` to async

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.4

## Acceptance Criteria
- All 5 tools converted to async
- All tools use connection pool
- All tools accept optional Context parameter
- Backward compatibility maintained
```

---

### Issue #5: Add MCP Resources

**Title**: feat: Implement MCP Resources for tables

**Labels**: `type: feature`, `phase: 1-foundation`, `component: resources`, `priority: medium`

**Description**:
```markdown
## Summary
Add MCP Resources to expose tables as browsable entities.

## Requirements
- [ ] Add `mssql://tables` resource (all tables)
- [ ] Add `mssql://tables/{schema}` resource (schema filter)
- [ ] Add `mssql://table/{schema}/{table}` resource (preview)
- [ ] Add `mssql://schema/{schema}/{table}` resource (columns)

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.5

## Acceptance Criteria
- Resources appear in `resources/list` response
- Resources can be read via `resources/read`
- Resources return valid JSON
- URI parameters are properly extracted
```

---

### Issue #6: Add Structured Logging

**Title**: feat: Add context-based logging to all tools

**Labels**: `type: feature`, `phase: 1-foundation`, `component: tools`, `priority: medium`

**Description**:
```markdown
## Summary
Add logging via FastMCP Context to all tools for debugging and monitoring.

## Requirements
- [ ] Add `ctx.info()` for normal operations
- [ ] Add `ctx.debug()` for detailed tracing
- [ ] Add `ctx.warning()` for security violations
- [ ] Add `ctx.error()` for errors
- [ ] Log query timing

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 1.6

## Acceptance Criteria
- All tools log at appropriate levels
- Query timing is logged
- Security violations are logged as warnings
- Errors are logged with details
```

---

## Phase 2 Issues (Features)

### Issue #7: Add ListIndexes Tool

**Title**: feat: Add ListIndexes tool for index discovery

**Labels**: `type: feature`, `phase: 2-features`, `component: tools`, `priority: medium`

**Description**:
```markdown
## Summary
Add a tool to list indexes defined on a table.

## Requirements
- [ ] Create `ListIndexes(table_name)` tool
- [ ] Return index name, type, columns
- [ ] Include uniqueness and primary key flags

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 2.1
```

---

### Issue #8: Add ListConstraints Tool

**Title**: feat: Add ListConstraints tool for constraint discovery

**Labels**: `type: feature`, `phase: 2-features`, `component: tools`, `priority: medium`

**Description**:
```markdown
## Summary
Add a tool to list constraints (CHECK, DEFAULT, UNIQUE) on a table.

## Requirements
- [ ] Create `ListConstraints(table_name)` tool
- [ ] Return constraint name, type, definition
- [ ] Include column associations
```

---

### Issue #9: Add ListStoredProcedures Tool

**Title**: feat: Add ListStoredProcedures tool

**Labels**: `type: feature`, `phase: 2-features`, `component: tools`, `priority: low`

**Description**:
```markdown
## Summary
Add a tool to list stored procedures in the database.

## Requirements
- [ ] Create `ListStoredProcedures(schema_filter)` tool
- [ ] Return procedure name and parameters
- [ ] Support schema filtering
```

---

### Issue #10: Add GetQueryPlan Tool

**Title**: feat: Add GetQueryPlan tool for query analysis

**Labels**: `type: feature`, `phase: 2-features`, `component: tools`, `priority: low`

**Description**:
```markdown
## Summary
Add a tool to get the estimated execution plan for SELECT queries.

## Requirements
- [ ] Create `GetQueryPlan(query)` tool
- [ ] Security: only allow SELECT queries
- [ ] Return execution plan in readable format
```

---

## Phase 3 Issues (Production)

### Issue #11: Add Mock Database Test Fixtures

**Title**: test: Add mock database fixtures for integration tests

**Labels**: `type: test`, `phase: 3-production`, `component: tests`, `priority: high`

**Description**:
```markdown
## Summary
Create pytest fixtures for testing tools without a real database.

## Requirements
- [ ] Create `mock_connection` fixture
- [ ] Create `mock_pool` fixture
- [ ] Create `mock_context` fixture
- [ ] Add `pytest-asyncio` dependency

## Technical Details
See: docs/IMPLEMENTATION_PLAN.md - Task 3.1
```

---

### Issue #12: Add Integration Tests for All Tools

**Title**: test: Add integration tests for all tools

**Labels**: `type: test`, `phase: 3-production`, `component: tests`, `priority: high`

**Description**:
```markdown
## Summary
Add comprehensive integration tests using mock fixtures.

## Requirements
- [ ] Test ListTables with mock data
- [ ] Test ListViews with mock data
- [ ] Test DescribeTable with mock data
- [ ] Test GetTableRelationships with mock data
- [ ] Test ReadData with various queries
- [ ] Test security filtering edge cases
- [ ] Achieve 80%+ code coverage
```

---

### Issue #13: Add CLI Configuration Options

**Title**: feat: Add CLI arguments for configuration

**Labels**: `type: feature`, `phase: 3-production`, `component: database`, `priority: medium`

**Description**:
```markdown
## Summary
Support command-line arguments for server configuration.

## Requirements
- [ ] Add `--server` argument
- [ ] Add `--database` argument
- [ ] Add `--driver` argument
- [ ] CLI args override environment variables
```

---

### Issue #14: Add Typed Error Classes

**Title**: refactor: Add typed error classes

**Labels**: `type: refactor`, `phase: 3-production`, `component: security`, `priority: medium`

**Description**:
```markdown
## Summary
Create specific error types for better error handling.

## Requirements
- [ ] Create `ConnectionError` class
- [ ] Create `QueryError` class
- [ ] Create `SecurityError` class
- [ ] Update tools to use typed errors
```

---

## Issue Template

Use this template for new issues:

```markdown
## Summary
[Brief description of what this issue addresses]

## Requirements
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

## Technical Details
[Link to relevant documentation or code references]

## Acceptance Criteria
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

## Related Issues
- Depends on: #X
- Blocks: #Y
```

---

## Milestone Tracking

### v0.2.0 - Foundation
- [ ] #1 Lifespan Manager
- [ ] #2 Connection Pool
- [ ] #3 Async Execution
- [ ] #4 Async Tools
- [ ] #5 MCP Resources
- [ ] #6 Structured Logging

### v0.3.0 - Features
- [ ] #7 ListIndexes
- [ ] #8 ListConstraints
- [ ] #9 ListStoredProcedures
- [ ] #10 GetQueryPlan

### v0.4.0 - Production
- [ ] #11 Mock Fixtures
- [ ] #12 Integration Tests
- [ ] #13 CLI Config
- [ ] #14 Typed Errors

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-11 | 1.0 | Initial issues guide |
