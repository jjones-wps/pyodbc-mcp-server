# Phase 2 Implementation Plan

**Goal**: Feature Completeness - Comprehensive SQL Server schema discovery

**Target Version**: v0.3.0

**Status**: 🟡 In Progress - Starting with ListIndexes tool

---

## Overview

Phase 2 adds comprehensive metadata discovery tools to make the MCP server feature-complete for SQL Server schema exploration. This phase builds on the Phase 1 foundation (async architecture, per-request connections, MCP resources).

---

## Implementation Strategy

### Architecture Pattern

All new tools follow the established pattern from Phase 1:

```python
@mcp.tool()
async def ToolName(args: type) -> str:
    """Tool description (imperative mood, PEP 257)."""
    logger.debug(f"ToolName called with {args}")

    def _query() -> result_type:
        """Execute query with per-request connection (thread-safe)."""
        conn = create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            # Process results
            return results
        finally:
            conn.close()

    results = await run_in_thread(_query)
    return json.dumps(result_dict, indent=2)
```

**Key Principles**:
- Per-request connections (thread-safe by design)
- Windows ODBC Driver handles pooling at driver level
- Async wrapper via `run_in_thread()` using `anyio.to_thread`
- Consistent logging with `logger.debug()`
- JSON output with 2-space indentation
- PEP 257 docstrings (imperative mood)

---

## Phase 2.1: Additional Metadata Tools

### Tool 1: ListIndexes ✅ In Progress

**Purpose**: Get indexes defined on a table with columns and types

**Signature**:
```python
async def ListIndexes(table_name: str) -> str
```

**Parameters**:
- `table_name`: Table name (can include schema, e.g., 'dbo.customers')

**Output Format**:
```json
{
  "table": "dbo.customers",
  "index_count": 3,
  "indexes": [
    {
      "name": "PK_customers",
      "type": "CLUSTERED",
      "is_unique": true,
      "is_primary_key": true,
      "columns": "customer_id"
    },
    {
      "name": "IX_customers_email",
      "type": "NONCLUSTERED",
      "is_unique": true,
      "is_primary_key": false,
      "columns": "email"
    }
  ]
}
```

**SQL Query**:
```sql
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
```

---

### Tool 2: ListConstraints

**Purpose**: Get constraints defined on a table (CHECK, UNIQUE, DEFAULT)

**Signature**:
```python
async def ListConstraints(table_name: str) -> str
```

**Parameters**:
- `table_name`: Table name (can include schema)

**Output Format**:
```json
{
  "table": "dbo.orders",
  "constraint_count": 2,
  "constraints": [
    {
      "name": "CK_orders_quantity",
      "type": "CHECK",
      "column": "quantity",
      "definition": "([quantity]>(0))"
    },
    {
      "name": "DF_orders_status",
      "type": "DEFAULT",
      "column": "status",
      "definition": "('pending')"
    }
  ]
}
```

**SQL Query**:
```sql
SELECT
    tc.CONSTRAINT_NAME,
    tc.CONSTRAINT_TYPE,
    ccu.COLUMN_NAME,
    cc.CHECK_CLAUSE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
LEFT JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
    ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
    ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
WHERE tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ?
  AND tc.CONSTRAINT_TYPE IN ('CHECK', 'UNIQUE', 'DEFAULT')
ORDER BY tc.CONSTRAINT_TYPE, tc.CONSTRAINT_NAME
```

---

### Tool 3: ListStoredProcedures

**Purpose**: List stored procedures in the database with parameter information

**Signature**:
```python
async def ListStoredProcedures(schema_filter: str | None = None) -> str
```

**Parameters**:
- `schema_filter`: Optional schema to filter (e.g., 'dbo')

**Output Format**:
```json
{
  "database": "MyDB",
  "procedure_count": 2,
  "procedures": [
    {
      "schema": "dbo",
      "name": "GetCustomerOrders",
      "parameters": "@CustomerID int, @StartDate datetime"
    },
    {
      "schema": "dbo",
      "name": "UpdateInventory",
      "parameters": "@ProductID int, @Quantity int"
    }
  ]
}
```

**SQL Query**:
```sql
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
```

---

### Tool 4: ListFunctions

**Purpose**: List user-defined functions in the database

**Signature**:
```python
async def ListFunctions(schema_filter: str | None = None) -> str
```

**Parameters**:
- `schema_filter`: Optional schema to filter (e.g., 'dbo')

**Output Format**:
```json
{
  "database": "MyDB",
  "function_count": 1,
  "functions": [
    {
      "schema": "dbo",
      "name": "CalculateDiscount",
      "type": "SCALAR_FUNCTION",
      "parameters": "@Amount decimal, @Percentage decimal"
    }
  ]
}
```

**SQL Query**:
```sql
SELECT
    SCHEMA_NAME(o.schema_id) AS schema_name,
    o.name AS function_name,
    o.type_desc AS function_type,
    STUFF((
        SELECT ', ' + par.name + ' ' + TYPE_NAME(par.user_type_id)
        FROM sys.parameters par
        WHERE par.object_id = o.object_id
        ORDER BY par.parameter_id
        FOR XML PATH('')
    ), 1, 2, '') AS parameters
FROM sys.objects o
WHERE o.type IN ('FN', 'IF', 'TF')
  AND SCHEMA_NAME(o.schema_id) = COALESCE(?, SCHEMA_NAME(o.schema_id))
ORDER BY schema_name, function_name
```

---

### Tool 5: GetQueryPlan

**Purpose**: Get the estimated execution plan for a SELECT query

**Signature**:
```python
async def GetQueryPlan(query: str) -> str
```

**Parameters**:
- `query`: SELECT query to analyze

**Security**: Must validate query starts with SELECT

**Output Format**:
```json
{
  "query": "SELECT * FROM customers WHERE ...",
  "execution_plan": [
    "Clustered Index Scan(OBJECT:([dbo].[customers].[PK_customers]))",
    "Cost: 0.0032831"
  ]
}
```

**Implementation Note**:
Uses SET SHOWPLAN_TEXT ON to get textual execution plan. Requires special handling as SHOWPLAN returns plan as result set, not regular rows.

---

## Phase 2.2: Enhanced Existing Tools

### Enhancement 1: DescribeTable - Add Primary Key Indicator

**Current Output**:
```json
{
  "name": "customer_id",
  "type": "int",
  "nullable": false
}
```

**Enhanced Output**:
```json
{
  "name": "customer_id",
  "type": "int",
  "nullable": false,
  "is_primary_key": true
}
```

**Implementation**: Join with INFORMATION_SCHEMA.KEY_COLUMN_USAGE to identify PK columns

---

### Enhancement 2: DescribeTable - Add Foreign Key References

**Enhanced Output**:
```json
{
  "name": "customer_id",
  "type": "int",
  "nullable": false,
  "foreign_key": {
    "references_table": "dbo.customers",
    "references_column": "id"
  }
}
```

**Implementation**: Join with sys.foreign_keys and sys.foreign_key_columns

---

### Enhancement 3: GetTableRelationships - Add Cardinality Hints

**Current Output**:
```json
{
  "from_table": "orders",
  "from_column": "customer_id",
  "to_table": "customers",
  "to_column": "id"
}
```

**Enhanced Output**:
```json
{
  "from_table": "orders",
  "from_column": "customer_id",
  "to_table": "customers",
  "to_column": "id",
  "cardinality": "many-to-one"
}
```

**Implementation**: Use uniqueness constraints to infer cardinality

---

### Enhancement 4: ReadData - Add Column Type Metadata

**Current Output**:
```json
{
  "row_count": 2,
  "rows": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ]
}
```

**Enhanced Output**:
```json
{
  "row_count": 2,
  "columns": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "varchar"}
  ],
  "rows": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ]
}
```

**Implementation**: Extract cursor.description metadata

---

## Phase 2.3: Input/Output Schemas

**Status**: Deferred to later in Phase 2

Pydantic models and JSON Schema will be added after the core tools are implemented and tested. This ensures we have stable interfaces before formalizing schemas.

---

## Testing Strategy

### Unit Tests

Each new tool gets a test in `tests/test_phase2.py`:

```python
class TestListIndexes:
    def test_parses_schema_table_format(self):
        # Test schema.table parsing
        pass

    def test_handles_missing_table(self):
        # Test error handling
        pass
```

### Integration Tests

Requires mock pyodbc connection fixture (deferred to Phase 3).

---

## Implementation Order

1. ✅ **ListIndexes** - Core metadata tool (IN PROGRESS)
2. **ListConstraints** - Core metadata tool
3. **DescribeTable enhancements** - Add PK and FK info
4. **ListStoredProcedures** - P21 systems heavily use SPs
5. **ListFunctions** - Less common, lower priority
6. **GetTableRelationships enhancements** - Add cardinality
7. **ReadData enhancements** - Add column metadata
8. **GetQueryPlan** - Advanced feature, implement last

---

## Success Criteria

- [ ] All 5 new tools implemented and working
- [ ] All 3 existing tools enhanced
- [ ] Tests added for new tools (unit tests minimum)
- [ ] CHANGELOG.md updated with Phase 2 features
- [ ] v0.3.0 release prepared
- [ ] All tools follow PEP 257 docstring standards
- [ ] Coverage threshold maintained (15% minimum)

---

## Version Target

**Release**: v0.3.0 - Feature Completeness

**Dependencies**: No new dependencies required (using existing fastmcp, pyodbc, anyio)

**Breaking Changes**: None (purely additive)

---

## Notes

- Phase 2 is purely additive - no breaking changes to existing tools
- All SQL queries use system views (INFORMATION_SCHEMA, sys.*) for broad compatibility
- Security model remains read-only (no EXEC, no modification)
- Connection pattern remains per-request (no pooling changes)
- Logging pattern remains consistent (logger.debug for operations)

---

**Created**: 2026-01-02
**Status**: Active Development
**Next Review**: After ListIndexes implementation
