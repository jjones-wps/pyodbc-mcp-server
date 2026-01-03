# Examples

Comprehensive examples and use cases for MSSQL MCP Server.

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [Schema Discovery](#schema-discovery)
- [Data Exploration](#data-exploration)
- [Relationship Mapping](#relationship-mapping)
- [Index Analysis](#index-analysis)
- [Constraint Checking](#constraint-checking)
- [Performance Analysis](#performance-analysis)
- [Integration with Claude Code](#integration-with-claude-code)
- [Advanced Use Cases](#advanced-use-cases)

---

## Quick Start Examples

### Connect and List Tables

```python
from mcp import MCP

# Initialize MCP client
mcp = MCP()

# List all tables
result = await mcp.call_tool("ListTables")
print(result)
```

**Output:**
```json
{
  "database": "AdventureWorks",
  "table_count": 71,
  "tables": [
    {"schema": "dbo", "table_name": "Users", "type": "BASE TABLE"},
    {"schema": "dbo", "table_name": "Orders", "type": "BASE TABLE"},
    {"schema": "sales", "table_name": "Customers", "type": "BASE TABLE"}
  ]
}
```

---

### Get Table Schema

```python
# Describe table structure
result = await mcp.call_tool("DescribeTable", {"table_name": "dbo.Users"})
print(result)
```

**Output:**
```json
{
  "table_name": "dbo.Users",
  "column_count": 5,
  "columns": [
    {
      "column_name": "UserId",
      "data_type": "int",
      "is_nullable": false,
      "is_primary_key": "✓"
    },
    {
      "column_name": "Username",
      "data_type": "nvarchar",
      "max_length": 100,
      "is_nullable": false
    }
  ],
  "primary_keys": ["UserId"],
  "foreign_keys": []
}
```

---

### Query Data

```python
# Execute SELECT query
result = await mcp.call_tool("ReadData", {
    "query": "SELECT TOP 10 UserId, Username FROM dbo.Users ORDER BY UserId",
    "max_rows": 10
})
print(result)
```

**Output:**
```json
{
  "query": "SELECT TOP 10 UserId, Username FROM dbo.Users ORDER BY UserId",
  "row_count": 10,
  "columns": ["UserId", "Username"],
  "rows": [
    {"UserId": 1, "Username": "alice"},
    {"UserId": 2, "Username": "bob"}
  ]
}
```

---

## Schema Discovery

### Explore Database Structure

**Use Case:** New developer needs to understand database schema

```python
# Step 1: List all schemas
result = await mcp.call_tool("ReadData", {
    "query": "SELECT DISTINCT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_SCHEMA"
})
# Output: ["dbo", "sales", "hr", "inventory"]

# Step 2: List tables in each schema
result = await mcp.call_tool("ListTables", {"schema_filter": "sales"})
# Output: sales.Customers, sales.Orders, sales.OrderDetails

# Step 3: Describe key tables
result = await mcp.call_tool("DescribeTable", {"table_name": "sales.Orders"})
```

---

### Find Tables by Name Pattern

**Use Case:** Find all tables related to "inventory"

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%inventory%'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
})
```

**Output:**
```json
{
  "rows": [
    {"TABLE_SCHEMA": "dbo", "TABLE_NAME": "InventoryLocations", "TABLE_TYPE": "BASE TABLE"},
    {"TABLE_SCHEMA": "warehouse", "TABLE_NAME": "InventoryAudit", "TABLE_TYPE": "BASE TABLE"}
  ]
}
```

---

### Discover All Foreign Keys

**Use Case:** Map all relationships in database

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            fk.name AS ForeignKey,
            OBJECT_SCHEMA_NAME(fk.parent_object_id) + '.' + OBJECT_NAME(fk.parent_object_id) AS ChildTable,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS ChildColumn,
            OBJECT_SCHEMA_NAME(fk.referenced_object_id) + '.' + OBJECT_NAME(fk.referenced_object_id) AS ParentTable,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ParentColumn
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        ORDER BY ChildTable, ParentTable
    """
})
```

---

## Data Exploration

### Sample Data from Each Table

**Use Case:** Preview data from all tables

```python
# Get list of tables
tables_result = await mcp.call_tool("ListTables")
tables = tables_result["tables"]

# Sample 5 rows from each table
for table in tables:
    table_name = f"{table['schema']}.{table['table_name']}"
    print(f"\n--- {table_name} ---")

    result = await mcp.call_tool("ReadData", {
        "query": f"SELECT TOP 5 * FROM {table_name}",
        "max_rows": 5
    })
    print(result)
```

---

### Find Null Values

**Use Case:** Data quality check - find columns with null values

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            UserId,
            Username,
            Email,
            DepartmentId,
            CreatedDate
        FROM dbo.Users
        WHERE Email IS NULL
           OR DepartmentId IS NULL
    """
})
```

---

### Aggregate Statistics

**Use Case:** Get summary statistics for numerical columns

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            COUNT(*) AS TotalOrders,
            SUM(TotalAmount) AS TotalRevenue,
            AVG(TotalAmount) AS AvgOrderValue,
            MIN(TotalAmount) AS MinOrder,
            MAX(TotalAmount) AS MaxOrder,
            MIN(OrderDate) AS FirstOrder,
            MAX(OrderDate) AS LastOrder
        FROM sales.Orders
    """
})
```

**Output:**
```json
{
  "rows": [{
    "TotalOrders": 15632,
    "TotalRevenue": 2847563.42,
    "AvgOrderValue": 182.15,
    "MinOrder": 10.50,
    "MaxOrder": 9875.00,
    "FirstOrder": "2020-01-05",
    "LastOrder": "2025-12-30"
  }]
}
```

---

### Group By Analysis

**Use Case:** Sales by customer segment

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            c.CustomerSegment,
            COUNT(DISTINCT o.CustomerId) AS CustomerCount,
            COUNT(o.OrderId) AS OrderCount,
            SUM(o.TotalAmount) AS TotalRevenue,
            AVG(o.TotalAmount) AS AvgOrderValue
        FROM sales.Orders o
        JOIN sales.Customers c ON o.CustomerId = c.CustomerId
        WHERE o.OrderDate >= '2025-01-01'
        GROUP BY c.CustomerSegment
        ORDER BY TotalRevenue DESC
    """
})
```

---

## Relationship Mapping

### Visualize Table Relationships

**Use Case:** Understand entity relationships

```python
# Get relationships for Orders table
result = await mcp.call_tool("GetTableRelationships", {
    "table_name": "sales.Orders"
})
```

**Output:**
```json
{
  "table_name": "sales.Orders",
  "outgoing_relationships": [
    {
      "constraint_name": "FK_Orders_Customers",
      "columns": ["CustomerId"],
      "referenced_table": "sales.Customers",
      "referenced_columns": ["CustomerId"],
      "on_delete": "CASCADE",
      "on_update": "NO ACTION"
    },
    {
      "constraint_name": "FK_Orders_Employees",
      "columns": ["EmployeeId"],
      "referenced_table": "hr.Employees",
      "referenced_columns": ["EmployeeId"],
      "on_delete": "SET NULL",
      "on_update": "CASCADE"
    }
  ],
  "incoming_relationships": [
    {
      "constraint_name": "FK_OrderDetails_Orders",
      "referencing_table": "sales.OrderDetails",
      "columns": ["OrderId"],
      "referenced_columns": ["OrderId"],
      "on_delete": "CASCADE"
    }
  ]
}
```

---

### Build Entity Relationship Diagram (ERD)

**Use Case:** Generate ERD data programmatically

```python
# Get all tables
tables = await mcp.call_tool("ListTables")

# For each table, get relationships
erd_data = {}
for table in tables["tables"]:
    table_name = f"{table['schema']}.{table['table_name']}"
    relationships = await mcp.call_tool("GetTableRelationships", {
        "table_name": table_name
    })
    erd_data[table_name] = relationships

# Now you can visualize erd_data with tools like Graphviz or Mermaid
```

---

### Find Orphaned Records

**Use Case:** Data integrity check - find orders without customers

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            o.OrderId,
            o.CustomerId,
            o.OrderDate
        FROM sales.Orders o
        LEFT JOIN sales.Customers c ON o.CustomerId = c.CustomerId
        WHERE c.CustomerId IS NULL
    """
})
```

---

## Index Analysis

### List All Indexes for Table

**Use Case:** Performance tuning - understand current indexes

```python
result = await mcp.call_tool("ListIndexes", {
    "table_name": "sales.Orders"
})
```

**Output:**
```json
{
  "table_name": "sales.Orders",
  "index_count": 5,
  "indexes": [
    {
      "index_name": "PK_Orders",
      "type": "CLUSTERED",
      "columns": ["OrderId"],
      "is_unique": true,
      "is_primary_key": true
    },
    {
      "index_name": "IX_Orders_Customer",
      "type": "NONCLUSTERED",
      "columns": ["CustomerId"],
      "is_unique": false,
      "is_primary_key": false
    },
    {
      "index_name": "IX_Orders_Date_Customer",
      "type": "NONCLUSTERED",
      "columns": ["OrderDate", "CustomerId"],
      "is_unique": false,
      "is_primary_key": false
    }
  ]
}
```

---

### Find Tables Without Indexes

**Use Case:** Identify tables that might benefit from indexing

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            SCHEMA_NAME(t.schema_id) AS SchemaName,
            t.name AS TableName,
            (SELECT COUNT(*) FROM sys.indexes i WHERE i.object_id = t.object_id) AS IndexCount
        FROM sys.tables t
        WHERE (SELECT COUNT(*) FROM sys.indexes i WHERE i.object_id = t.object_id AND i.type > 0) = 0
        ORDER BY SchemaName, TableName
    """
})
```

---

### Index Usage Statistics

**Use Case:** Find unused indexes (candidates for removal)

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            OBJECT_SCHEMA_NAME(i.object_id) + '.' + OBJECT_NAME(i.object_id) AS TableName,
            i.name AS IndexName,
            i.type_desc AS IndexType,
            ius.user_seeks,
            ius.user_scans,
            ius.user_lookups,
            ius.user_updates,
            ius.last_user_seek,
            ius.last_user_scan
        FROM sys.indexes i
        LEFT JOIN sys.dm_db_index_usage_stats ius
            ON i.object_id = ius.object_id
            AND i.index_id = ius.index_id
            AND ius.database_id = DB_ID()
        WHERE i.type > 0  -- Exclude heaps
          AND OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
        ORDER BY
            (ISNULL(ius.user_seeks, 0) + ISNULL(ius.user_scans, 0) + ISNULL(ius.user_lookups, 0)) ASC,
            ius.user_updates DESC
    """,
    "max_rows": 50
})
```

---

## Constraint Checking

### List All Constraints for Table

**Use Case:** Understand business rules enforced by database

```python
result = await mcp.call_tool("ListConstraints", {
    "table_name": "sales.Orders"
})
```

**Output:**
```json
{
  "table_name": "sales.Orders",
  "constraint_count": 6,
  "constraints": [
    {
      "constraint_name": "PK_Orders",
      "constraint_type": "PRIMARY KEY",
      "columns": ["OrderId"]
    },
    {
      "constraint_name": "FK_Orders_Customers",
      "constraint_type": "FOREIGN KEY",
      "columns": ["CustomerId"]
    },
    {
      "constraint_name": "UQ_Orders_OrderNumber",
      "constraint_type": "UNIQUE",
      "columns": ["OrderNumber"]
    },
    {
      "constraint_name": "CK_Orders_Quantity",
      "constraint_type": "CHECK",
      "columns": ["Quantity"],
      "definition": "([Quantity]>(0))"
    },
    {
      "constraint_name": "CK_Orders_Status",
      "constraint_type": "CHECK",
      "columns": ["Status"],
      "definition": "([Status] IN ('Pending','Shipped','Delivered','Cancelled'))"
    },
    {
      "constraint_name": "DF_Orders_OrderDate",
      "constraint_type": "DEFAULT",
      "columns": ["OrderDate"],
      "definition": "(getdate())"
    }
  ]
}
```

---

### Find Check Constraint Violations

**Use Case:** Data quality audit - find rows that would violate constraints if enabled

```python
# Check for negative quantities (would violate CK_Orders_Quantity if enabled)
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            OrderId,
            Quantity,
            TotalAmount
        FROM sales.Orders
        WHERE Quantity <= 0
           OR TotalAmount < 0
    """
})
```

---

### Validate Foreign Key Integrity

**Use Case:** Find referential integrity issues

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        -- Find Orders with non-existent CustomerId
        SELECT
            o.OrderId,
            o.CustomerId AS InvalidCustomerId,
            o.OrderDate
        FROM sales.Orders o
        WHERE NOT EXISTS (
            SELECT 1 FROM sales.Customers c WHERE c.CustomerId = o.CustomerId
        )
    """
})
```

---

## Performance Analysis

### Table Size Analysis

**Use Case:** Identify largest tables in database

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            SCHEMA_NAME(t.schema_id) AS SchemaName,
            t.name AS TableName,
            SUM(p.rows) AS RowCount,
            SUM(a.total_pages) * 8 / 1024 AS TotalSpaceMB,
            SUM(a.used_pages) * 8 / 1024 AS UsedSpaceMB,
            (SUM(a.total_pages) - SUM(a.used_pages)) * 8 / 1024 AS UnusedSpaceMB
        FROM sys.tables t
        INNER JOIN sys.partitions p ON t.object_id = p.object_id
        INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
        WHERE p.index_id IN (0, 1)  -- Heap or clustered index
        GROUP BY t.schema_id, t.name
        ORDER BY SUM(a.total_pages) DESC
    """,
    "max_rows": 20
})
```

**Output:**
```json
{
  "rows": [
    {
      "SchemaName": "sales",
      "TableName": "OrderHistory",
      "RowCount": 5247893,
      "TotalSpaceMB": 8432,
      "UsedSpaceMB": 7854,
      "UnusedSpaceMB": 578
    },
    {
      "SchemaName": "audit",
      "TableName": "UserActivity",
      "RowCount": 12458921,
      "TotalSpaceMB": 6721,
      "UsedSpaceMB": 6512,
      "UnusedSpaceMB": 209
    }
  ]
}
```

---

### Query Execution Time Analysis

**Use Case:** Find slow-running queries

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT TOP 20
            CAST(qs.total_elapsed_time / 1000000.0 AS DECIMAL(10,2)) AS total_elapsed_seconds,
            CAST(qs.total_elapsed_time / qs.execution_count / 1000000.0 AS DECIMAL(10,2)) AS avg_elapsed_seconds,
            qs.execution_count,
            SUBSTRING(qt.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                  WHEN -1 THEN DATALENGTH(qt.text)
                  ELSE qs.statement_end_offset
                END - qs.statement_start_offset)/2) + 1) AS query_text,
            qs.creation_time,
            qs.last_execution_time
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
        WHERE qt.text NOT LIKE '%dm_exec_query_stats%'  -- Exclude this query
        ORDER BY qs.total_elapsed_time DESC
    """,
    "max_rows": 20
})
```

---

### Database Growth Trend

**Use Case:** Predict storage requirements

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            DB_NAME() AS DatabaseName,
            (SUM(size) * 8.0 / 1024) AS CurrentSizeMB,
            (SUM(CASE WHEN max_size = -1 THEN size ELSE max_size END) * 8.0 / 1024) AS MaxSizeMB,
            (SUM(size) * 8.0 / 1024 / NULLIF(SUM(CASE WHEN max_size = -1 THEN size ELSE max_size END) * 8.0 / 1024, 0) * 100) AS PercentUsed
        FROM sys.database_files
        WHERE type_desc = 'ROWS'
    """
})
```

---

## Integration with Claude Code

### Auto-Generate Documentation

**Use Case:** Document database schema for new developers

```python
# Get all tables
tables = await mcp.call_tool("ListTables")

# For each table, generate documentation
documentation = []
for table in tables["tables"]:
    table_name = f"{table['schema']}.{table['table_name']}"

    # Get schema
    schema = await mcp.call_tool("DescribeTable", {"table_name": table_name})

    # Get relationships
    relationships = await mcp.call_tool("GetTableRelationships", {"table_name": table_name})

    # Get constraints
    constraints = await mcp.call_tool("ListConstraints", {"table_name": table_name})

    # Get indexes
    indexes = await mcp.call_tool("ListIndexes", {"table_name": table_name})

    # Build markdown documentation
    doc = f"""
## {table_name}

**Columns:** {schema['column_count']}
**Primary Key:** {', '.join(schema['primary_keys'])}
**Foreign Keys:** {len(schema['foreign_keys'])}
**Indexes:** {indexes['index_count']}
**Constraints:** {constraints['constraint_count']}

### Schema
```
{format_schema(schema)}
```

### Relationships
{format_relationships(relationships)}

### Indexes
{format_indexes(indexes)}
"""
    documentation.append(doc)

# Save to file
with open("database_documentation.md", "w") as f:
    f.write("\n".join(documentation))
```

---

### Code Generation from Schema

**Use Case:** Generate TypeScript interfaces from database tables

```python
# Get table schema
schema = await mcp.call_tool("DescribeTable", {"table_name": "sales.Orders"})

# Generate TypeScript interface
def generate_typescript_interface(schema):
    lines = [f"export interface {schema['table_name'].split('.')[-1]} {{"]

    for column in schema['columns']:
        ts_type = map_sql_to_typescript(column['data_type'])
        optional = "?" if column['is_nullable'] else ""
        lines.append(f"  {column['column_name']}{optional}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)

def map_sql_to_typescript(sql_type):
    mapping = {
        "int": "number",
        "bigint": "number",
        "decimal": "number",
        "float": "number",
        "nvarchar": "string",
        "varchar": "string",
        "datetime": "Date",
        "bit": "boolean"
    }
    return mapping.get(sql_type.lower(), "unknown")

print(generate_typescript_interface(schema))
```

**Output:**
```typescript
export interface Orders {
  OrderId: number;
  CustomerId: number;
  OrderDate: Date;
  TotalAmount: number;
  Status: string;
}
```

---

### Database Migration Assistant

**Use Case:** Compare schemas across environments

```python
# Compare production vs staging schemas
prod_schema = await mcp_prod.call_tool("DescribeTable", {"table_name": "sales.Orders"})
staging_schema = await mcp_staging.call_tool("DescribeTable", {"table_name": "sales.Orders"})

# Find differences
def compare_schemas(prod, staging):
    prod_columns = {col['column_name']: col for col in prod['columns']}
    staging_columns = {col['column_name']: col for col in staging['columns']}

    # Missing in staging
    missing = set(prod_columns.keys()) - set(staging_columns.keys())

    # Extra in staging
    extra = set(staging_columns.keys()) - set(prod_columns.keys())

    # Different data types
    different = []
    for col_name in prod_columns:
        if col_name in staging_columns:
            if prod_columns[col_name]['data_type'] != staging_columns[col_name]['data_type']:
                different.append({
                    'column': col_name,
                    'prod_type': prod_columns[col_name]['data_type'],
                    'staging_type': staging_columns[col_name]['data_type']
                })

    return {
        'missing_in_staging': list(missing),
        'extra_in_staging': list(extra),
        'type_differences': different
    }

differences = compare_schemas(prod_schema, staging_schema)
print(differences)
```

---

## Advanced Use Cases

### Data Lineage Tracking

**Use Case:** Trace data flow through views and stored procedures

```python
# Find all views that reference a table
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            OBJECT_SCHEMA_NAME(v.object_id) + '.' + OBJECT_NAME(v.object_id) AS ViewName,
            OBJECT_SCHEMA_NAME(d.referenced_id) + '.' + OBJECT_NAME(d.referenced_id) AS ReferencedTable
        FROM sys.views v
        INNER JOIN sys.sql_dependencies d ON v.object_id = d.object_id
        WHERE OBJECT_NAME(d.referenced_id) = 'Orders'
        ORDER BY ViewName
    """
})
```

---

### Change Data Capture (CDC) Analysis

**Use Case:** Identify tables with CDC enabled

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            SCHEMA_NAME(t.schema_id) + '.' + t.name AS TableName,
            cdc.capture_instance,
            cdc.start_lsn,
            cdc.create_date,
            CASE WHEN sys.fn_cdc_is_bit_set(cdc.supports_net_changes, 1) = 1
                 THEN 'Yes' ELSE 'No' END AS SupportsNetChanges
        FROM sys.tables t
        INNER JOIN cdc.change_tables cdc ON t.object_id = cdc.source_object_id
        ORDER BY TableName
    """
})
```

---

### Temporal Table History

**Use Case:** Query system-versioned temporal tables

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        -- Get current and historical data
        SELECT
            UserId,
            Username,
            Email,
            ValidFrom,
            ValidTo
        FROM dbo.Users
        FOR SYSTEM_TIME ALL
        WHERE UserId = 123
        ORDER BY ValidFrom DESC
    """
})
```

---

### JSON Data Extraction

**Use Case:** Query JSON columns

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            UserId,
            Username,
            JSON_VALUE(Preferences, '$.theme') AS Theme,
            JSON_VALUE(Preferences, '$.language') AS Language,
            JSON_QUERY(Preferences, '$.notifications') AS Notifications
        FROM dbo.Users
        WHERE JSON_VALUE(Preferences, '$.theme') = 'dark'
    """
})
```

---

### Full-Text Search

**Use Case:** Search across text columns

```python
result = await mcp.call_tool("ReadData", {
    "query": """
        SELECT
            ProductId,
            ProductName,
            Description,
            KEY_TBL.RANK AS SearchRank
        FROM Products
        INNER JOIN FREETEXTTABLE(Products, (ProductName, Description), 'wireless bluetooth speaker') AS KEY_TBL
            ON Products.ProductId = KEY_TBL.[KEY]
        ORDER BY KEY_TBL.RANK DESC
    """,
    "max_rows": 20
})
```

---

## See Also

- [API Reference](API.md) - Complete tool documentation
- [Configuration Guide](CONFIGURATION.md) - Server configuration
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [Development Guide](DEVELOPMENT.md) - Contributing to the project
