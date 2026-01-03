# API Reference

Complete reference documentation for all MCP tools and resources provided by MSSQL MCP Server.

## Table of Contents

- [Tools](#tools)
  - [ListTables](#listtables)
  - [DescribeTable](#describetable)
  - [ReadData](#readdata)
  - [GetTableRelationships](#gettablerelationships)
  - [ListViews](#listviews)
  - [ListIndexes](#listindexes)
  - [ListConstraints](#listconstraints)
  - [ListStoredProcedures](#liststoredprocedures)
  - [ListFunctions](#listfunctions)
  - [ListTriggers](#listtriggers)
- [Resources](#resources)
  - [mssql://tables](#mssqltables)
  - [mssql://views](#mssqlviews)
  - [mssql://schema/{schema_name}](#mssqlschemaschema_name)
  - [mssql://table/{table_name}/preview](#mssqltabletable_namepreview)
  - [mssql://info](#mssqlinfo)
- [Error Handling](#error-handling)
  - [Error Response Format](#error-response-format)
  - [Error Types](#error-types)
- [Security](#security)

---

## Tools

Tools are the primary interface for interacting with SQL Server. All tools support error handling with typed exceptions and return JSON-formatted responses.

### ListTables

List all tables in the database with optional schema filtering.

**Parameters:**
- `schema_filter` (string, optional): Filter tables to a specific schema (e.g., "dbo")

**Returns:** JSON object with table count and detailed table list

**Response Schema:**
```json
{
  "database": "string",
  "table_count": "number",
  "tables": [
    {
      "schema": "string",
      "table_name": "string",
      "type": "string (BASE TABLE or VIEW)"
    }
  ]
}
```

**Example Usage:**
```python
# List all tables
result = await ListTables()

# List only dbo schema tables
result = await ListTables(schema_filter="dbo")
```

**Example Response:**
```json
{
  "database": "AdventureWorks",
  "table_count": 71,
  "tables": [
    {
      "schema": "dbo",
      "table_name": "Users",
      "type": "BASE TABLE"
    },
    {
      "schema": "sales",
      "table_name": "Orders",
      "type": "BASE TABLE"
    }
  ]
}
```

---

### DescribeTable

Get detailed schema information about a specific table including columns, primary keys, and foreign keys.

**Parameters:**
- `table_name` (string, required): Table name with optional schema (e.g., "dbo.Users" or "Users")

**Returns:** JSON object with column definitions, primary keys, and foreign keys

**Response Schema:**
```json
{
  "table_name": "string",
  "column_count": "number",
  "columns": [
    {
      "column_name": "string",
      "data_type": "string",
      "max_length": "number",
      "precision": "number",
      "scale": "number",
      "is_nullable": "boolean",
      "is_primary_key": "boolean (✓ or ✗)",
      "is_foreign_key": "boolean (✓ or ✗)",
      "default_value": "string or null"
    }
  ],
  "primary_keys": ["string array of column names"],
  "foreign_keys": [
    {
      "column_name": "string",
      "referenced_table": "string",
      "referenced_column": "string"
    }
  ]
}
```

**Example Usage:**
```python
# Describe a table
result = await DescribeTable("dbo.Users")

# Without schema qualifier (uses default schema)
result = await DescribeTable("Users")
```

**Example Response:**
```json
{
  "table_name": "dbo.Users",
  "column_count": 5,
  "columns": [
    {
      "column_name": "UserId",
      "data_type": "int",
      "max_length": 4,
      "precision": 10,
      "scale": 0,
      "is_nullable": false,
      "is_primary_key": "✓",
      "is_foreign_key": "✗",
      "default_value": null
    },
    {
      "column_name": "Username",
      "data_type": "nvarchar",
      "max_length": 100,
      "precision": 0,
      "scale": 0,
      "is_nullable": false,
      "is_primary_key": "✗",
      "is_foreign_key": "✗",
      "default_value": null
    },
    {
      "column_name": "DepartmentId",
      "data_type": "int",
      "max_length": 4,
      "precision": 10,
      "scale": 0,
      "is_nullable": true,
      "is_primary_key": "✗",
      "is_foreign_key": "✓",
      "default_value": null
    }
  ],
  "primary_keys": ["UserId"],
  "foreign_keys": [
    {
      "column_name": "DepartmentId",
      "referenced_table": "dbo.Departments",
      "referenced_column": "DepartmentId"
    }
  ]
}
```

---

### ReadData

Execute a SELECT query and return results with configurable row limits.

**Parameters:**
- `query` (string, required): SQL SELECT query to execute
- `max_rows` (number, optional): Maximum number of rows to return (default: 100, max: 10000)

**Security:** Only SELECT queries are allowed. Queries containing forbidden keywords (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, EXEC, etc.) will be rejected with a SecurityError.

**Returns:** JSON object with query metadata and results

**Response Schema:**
```json
{
  "query": "string",
  "row_count": "number",
  "rows_returned": "number",
  "truncated": "boolean",
  "columns": ["string array of column names"],
  "rows": [
    {
      "column1": "value1",
      "column2": "value2"
    }
  ]
}
```

**Example Usage:**
```python
# Simple query
result = await ReadData("SELECT * FROM dbo.Users")

# Query with custom row limit
result = await ReadData("SELECT * FROM dbo.Orders", max_rows=500)

# Query with WHERE clause
result = await ReadData("SELECT UserId, Username FROM dbo.Users WHERE Active = 1")
```

**Example Response:**
```json
{
  "query": "SELECT UserId, Username FROM dbo.Users WHERE Active = 1",
  "row_count": 42,
  "rows_returned": 42,
  "truncated": false,
  "columns": ["UserId", "Username"],
  "rows": [
    {"UserId": 1, "Username": "alice"},
    {"UserId": 2, "Username": "bob"}
  ]
}
```

**Security Example (Rejected):**
```python
# This will raise SecurityError
result = await ReadData("SELECT * FROM Users; DROP TABLE Users")
```

**Error Response:**
```json
{
  "error": "SECURITY_ERROR",
  "message": "Query contains forbidden keyword 'DROP'. This server is read-only.",
  "details": {
    "query": "SELECT * FROM Users; DROP TABLE Users",
    "blocked_keyword": "DROP"
  }
}
```

---

### GetTableRelationships

Get foreign key relationships for a table (both incoming and outgoing) with referential actions and composite key support.

**Parameters:**
- `table_name` (string, required): Table name with optional schema (e.g., "dbo.Orders" or "Orders")

**Returns:** JSON object with outgoing and incoming foreign key relationships

**Response Schema:**
```json
{
  "table_name": "string",
  "outgoing_relationships": [
    {
      "constraint_name": "string",
      "columns": ["string array"],
      "referenced_table": "string",
      "referenced_columns": ["string array"],
      "on_delete": "NO ACTION | CASCADE | SET NULL | SET DEFAULT",
      "on_update": "NO ACTION | CASCADE | SET NULL | SET DEFAULT",
      "is_enabled": "boolean"
    }
  ],
  "incoming_relationships": [
    {
      "constraint_name": "string",
      "referencing_table": "string",
      "columns": ["string array"],
      "referenced_columns": ["string array"],
      "on_delete": "NO ACTION | CASCADE | SET NULL | SET DEFAULT",
      "on_update": "NO ACTION | CASCADE | SET NULL | SET DEFAULT",
      "is_enabled": "boolean"
    }
  ]
}
```

**Example Usage:**
```python
# Get relationships for a table
result = await GetTableRelationships("dbo.Orders")
```

**Example Response:**
```json
{
  "table_name": "dbo.Orders",
  "outgoing_relationships": [
    {
      "constraint_name": "FK_Orders_Customers",
      "columns": ["CustomerId"],
      "referenced_table": "dbo.Customers",
      "referenced_columns": ["CustomerId"],
      "on_delete": "CASCADE",
      "on_update": "NO ACTION",
      "is_enabled": true
    },
    {
      "constraint_name": "FK_Orders_Employees",
      "columns": ["EmployeeId"],
      "referenced_table": "dbo.Employees",
      "referenced_columns": ["EmployeeId"],
      "on_delete": "SET NULL",
      "on_update": "CASCADE",
      "is_enabled": true
    }
  ],
  "incoming_relationships": [
    {
      "constraint_name": "FK_OrderDetails_Orders",
      "referencing_table": "dbo.OrderDetails",
      "columns": ["OrderId"],
      "referenced_columns": ["OrderId"],
      "on_delete": "CASCADE",
      "on_update": "NO ACTION",
      "is_enabled": true
    }
  ]
}
```

**Composite Key Example:**
```json
{
  "constraint_name": "FK_OrderDetails_Products",
  "columns": ["ProductId", "WarehouseId"],
  "referenced_table": "dbo.Products",
  "referenced_columns": ["ProductId", "WarehouseId"],
  "on_delete": "NO ACTION",
  "on_update": "NO ACTION",
  "is_enabled": true
}
```

---

### ListViews

List all views in the database with optional schema filtering.

**Parameters:**
- `schema_filter` (string, optional): Filter views to a specific schema (e.g., "dbo")

**Returns:** JSON object with view count and detailed view list

**Response Schema:**
```json
{
  "database": "string",
  "view_count": "number",
  "views": [
    {
      "schema": "string",
      "view_name": "string"
    }
  ]
}
```

**Example Usage:**
```python
# List all views
result = await ListViews()

# List only dbo schema views
result = await ListViews(schema_filter="dbo")
```

**Example Response:**
```json
{
  "database": "AdventureWorks",
  "view_count": 12,
  "views": [
    {
      "schema": "dbo",
      "view_name": "vw_ActiveUsers"
    },
    {
      "schema": "sales",
      "view_name": "vw_OrderSummary"
    }
  ]
}
```

---

### ListIndexes

List all indexes for a specific table with detailed metadata.

**Parameters:**
- `table_name` (string, required): Table name with optional schema (e.g., "dbo.Users" or "Users")

**Returns:** JSON object with index count and detailed index list

**Response Schema:**
```json
{
  "table_name": "string",
  "index_count": "number",
  "indexes": [
    {
      "index_name": "string",
      "type": "CLUSTERED | NONCLUSTERED | UNIQUE CLUSTERED | UNIQUE NONCLUSTERED",
      "columns": ["string array"],
      "is_unique": "boolean",
      "is_primary_key": "boolean"
    }
  ]
}
```

**Example Usage:**
```python
# List indexes for a table
result = await ListIndexes("dbo.Users")
```

**Example Response:**
```json
{
  "table_name": "dbo.Users",
  "index_count": 3,
  "indexes": [
    {
      "index_name": "PK_Users",
      "type": "CLUSTERED",
      "columns": ["UserId"],
      "is_unique": true,
      "is_primary_key": true
    },
    {
      "index_name": "IX_Users_Username",
      "type": "NONCLUSTERED",
      "columns": ["Username"],
      "is_unique": true,
      "is_primary_key": false
    },
    {
      "index_name": "IX_Users_Department",
      "type": "NONCLUSTERED",
      "columns": ["DepartmentId", "CreatedDate"],
      "is_unique": false,
      "is_primary_key": false
    }
  ]
}
```

---

### ListConstraints

List all constraints for a specific table (primary keys, foreign keys, unique constraints, check constraints).

**Parameters:**
- `table_name` (string, required): Table name with optional schema (e.g., "dbo.Orders" or "Orders")

**Returns:** JSON object with constraint count and detailed constraint list

**Response Schema:**
```json
{
  "table_name": "string",
  "constraint_count": "number",
  "constraints": [
    {
      "constraint_name": "string",
      "constraint_type": "PRIMARY KEY | FOREIGN KEY | UNIQUE | CHECK",
      "columns": ["string array"],
      "definition": "string (for CHECK constraints)"
    }
  ]
}
```

**Example Usage:**
```python
# List constraints for a table
result = await ListConstraints("dbo.Orders")
```

**Example Response:**
```json
{
  "table_name": "dbo.Orders",
  "constraint_count": 4,
  "constraints": [
    {
      "constraint_name": "PK_Orders",
      "constraint_type": "PRIMARY KEY",
      "columns": ["OrderId"],
      "definition": null
    },
    {
      "constraint_name": "FK_Orders_Customers",
      "constraint_type": "FOREIGN KEY",
      "columns": ["CustomerId"],
      "definition": null
    },
    {
      "constraint_name": "UQ_Orders_OrderNumber",
      "constraint_type": "UNIQUE",
      "columns": ["OrderNumber"],
      "definition": null
    },
    {
      "constraint_name": "CK_Orders_Quantity",
      "constraint_type": "CHECK",
      "columns": ["Quantity"],
      "definition": "([Quantity]>(0))"
    }
  ]
}
```

---

### ListStoredProcedures

List all stored procedures in the database with optional schema filtering.

**Parameters:**
- `schema_filter` (string, optional): Filter procedures to a specific schema (e.g., "dbo")

**Returns:** JSON object with procedure count and detailed procedure list

**Response Schema:**
```json
{
  "database": "string",
  "procedure_count": "number",
  "procedures": [
    {
      "schema": "string",
      "procedure_name": "string",
      "created_date": "ISO 8601 datetime",
      "modified_date": "ISO 8601 datetime"
    }
  ]
}
```

**Example Usage:**
```python
# List all stored procedures
result = await ListStoredProcedures()

# List only dbo schema procedures
result = await ListStoredProcedures(schema_filter="dbo")
```

**Example Response:**
```json
{
  "database": "AdventureWorks",
  "procedure_count": 8,
  "procedures": [
    {
      "schema": "dbo",
      "procedure_name": "sp_GetUserById",
      "created_date": "2025-01-01T10:00:00",
      "modified_date": "2025-12-15T14:30:00"
    },
    {
      "schema": "sales",
      "procedure_name": "sp_CreateOrder",
      "created_date": "2025-06-10T09:15:00",
      "modified_date": "2025-12-20T11:00:00"
    }
  ]
}
```

---

### ListFunctions

List all user-defined functions in the database with optional schema filtering.

**Parameters:**
- `schema_filter` (string, optional): Filter functions to a specific schema (e.g., "dbo")

**Returns:** JSON object with function count and detailed function list

**Response Schema:**
```json
{
  "database": "string",
  "function_count": "number",
  "functions": [
    {
      "schema": "string",
      "function_name": "string",
      "type": "SCALAR_FUNCTION | TABLE_FUNCTION | INLINE_FUNCTION",
      "created_date": "ISO 8601 datetime",
      "modified_date": "ISO 8601 datetime"
    }
  ]
}
```

**Example Usage:**
```python
# List all functions
result = await ListFunctions()

# List only dbo schema functions
result = await ListFunctions(schema_filter="dbo")
```

**Example Response:**
```json
{
  "database": "AdventureWorks",
  "function_count": 5,
  "functions": [
    {
      "schema": "dbo",
      "function_name": "fn_CalculateDiscount",
      "type": "SCALAR_FUNCTION",
      "created_date": "2025-03-15T12:00:00",
      "modified_date": "2025-11-20T16:45:00"
    },
    {
      "schema": "sales",
      "function_name": "fn_GetOrdersByCustomer",
      "type": "TABLE_FUNCTION",
      "created_date": "2025-05-22T08:30:00",
      "modified_date": "2025-12-10T10:15:00"
    }
  ]
}
```

---

### ListTriggers

List all triggers in the database with optional schema filtering.

**Parameters:**
- `schema_filter` (string, optional): Filter triggers to a specific schema (e.g., "dbo")

**Returns:** JSON object with trigger count and detailed trigger list

**Response Schema:**
```json
{
  "database": "string",
  "trigger_count": "number",
  "triggers": [
    {
      "schema": "string",
      "trigger_name": "string",
      "table_name": "string",
      "is_enabled": "boolean",
      "created_date": "ISO 8601 datetime",
      "modified_date": "ISO 8601 datetime"
    }
  ]
}
```

**Example Usage:**
```python
# List all triggers
result = await ListTriggers()

# List only dbo schema triggers
result = await ListTriggers(schema_filter="dbo")
```

**Example Response:**
```json
{
  "database": "AdventureWorks",
  "trigger_count": 3,
  "triggers": [
    {
      "schema": "dbo",
      "trigger_name": "tr_Users_Audit",
      "table_name": "Users",
      "is_enabled": true,
      "created_date": "2025-02-10T14:00:00",
      "modified_date": "2025-10-05T09:30:00"
    },
    {
      "schema": "sales",
      "trigger_name": "tr_Orders_UpdateInventory",
      "table_name": "Orders",
      "is_enabled": true,
      "created_date": "2025-04-18T11:20:00",
      "modified_date": "2025-12-01T13:45:00"
    }
  ]
}
```

---

## Resources

Resources provide quick access to commonly used database metadata through URI-based endpoints.

### mssql://tables

List all tables in the database as a plain text resource.

**Response Format:** Plain text, one table per line in "schema.table_name" format

**Example Response:**
```
dbo.Users
dbo.Orders
dbo.Products
sales.OrderDetails
sales.Customers
```

---

### mssql://views

List all views in the database as a plain text resource.

**Response Format:** Plain text, one view per line in "schema.view_name" format

**Example Response:**
```
dbo.vw_ActiveUsers
dbo.vw_RecentOrders
sales.vw_CustomerSummary
```

---

### mssql://schema/{schema_name}

List all tables in a specific schema as a plain text resource.

**Parameters:**
- `schema_name` (string): Schema name (e.g., "dbo", "sales")

**Response Format:** Plain text, one table per line in "schema.table_name" format

**Example (mssql://schema/dbo):**
```
dbo.Users
dbo.Orders
dbo.Products
```

---

### mssql://table/{table_name}/preview

Get a preview of table data (first 10 rows) as a plain text resource.

**Parameters:**
- `table_name` (string): Table name with optional schema (e.g., "dbo.Users" or "Users")

**Response Format:** Plain text, pipe-delimited table format

**Example (mssql://table/dbo.Users/preview):**
```
UserId | Username | Email
-------|----------|-------
1      | alice    | alice@example.com
2      | bob      | bob@example.com
3      | charlie  | charlie@example.com
```

---

### mssql://info

Get database connection information as a plain text resource.

**Response Format:** Plain text, key-value pairs

**Example Response:**
```
Server: localhost
Database: AdventureWorks
Driver: ODBC Driver 17 for SQL Server
Connection: Trusted_Connection (Windows Auth)
```

---

## Error Handling

All tools implement comprehensive error handling with typed exceptions and consistent JSON responses.

### Error Response Format

When an error occurs, tools return a JSON object with the following structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

### Error Types

#### CONNECTION_ERROR

Raised when database connection fails.

**Example:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [08001] [Microsoft][ODBC Driver 17 for SQL Server]Named Pipes Provider: Could not open a connection to SQL Server",
  "details": {
    "server": "localhost",
    "database": "AdventureWorks",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Common Causes:**
- SQL Server is not running
- Incorrect server name or port
- Network connectivity issues
- Windows Authentication not configured

---

#### SECURITY_ERROR

Raised when a query violates read-only security constraints.

**Example:**
```json
{
  "error": "SECURITY_ERROR",
  "message": "Query contains forbidden keyword 'DELETE'. This server is read-only.",
  "details": {
    "query": "DELETE FROM Users WHERE UserId = 1",
    "blocked_keyword": "DELETE"
  }
}
```

**Blocked Keywords:**
- INSERT, UPDATE, DELETE
- DROP, CREATE, ALTER, TRUNCATE
- EXEC, EXECUTE, sp_executesql
- xp_cmdshell, OPENROWSET, OPENDATASOURCE

---

#### VALIDATION_ERROR

Raised when input parameters are invalid.

**Example:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "max_rows must be positive",
  "details": {
    "parameter": "max_rows",
    "value": "-5"
  }
}
```

**Common Validation Errors:**
- Negative max_rows values
- Empty query strings
- Invalid table names

---

#### QUERY_ERROR

Raised when SQL query execution fails.

**Example:**
```json
{
  "error": "QUERY_ERROR",
  "message": "Query failed: [42S02] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Invalid object name 'InvalidTable'",
  "details": {
    "query": "SELECT * FROM InvalidTable",
    "error_code": "42S02"
  }
}
```

**Common Causes:**
- Invalid table or column names
- Syntax errors in SQL
- Permission issues
- Schema doesn't exist

---

#### TIMEOUT_ERROR

Raised when query execution exceeds configured timeout.

**Example:**
```json
{
  "error": "TIMEOUT_ERROR",
  "message": "Query execution timed out after 30 seconds",
  "details": {
    "operation": "SELECT query",
    "timeout_seconds": "30"
  }
}
```

**Configuration:** Timeout can be configured via `query_timeout` parameter (see [CONFIGURATION.md](CONFIGURATION.md))

---

#### INTERNAL_ERROR

Raised for unexpected errors not covered by specific error types.

**Example:**
```json
{
  "error": "INTERNAL_ERROR",
  "message": "Unexpected error: division by zero",
  "details": {
    "type": "ZeroDivisionError"
  }
}
```

---

### Retry Logic

The server implements automatic retry logic for transient errors with exponential backoff:

- **Transient Error Codes:** 08S01 (Communication link failure), 08001 (Connection failure), HYT00 (Timeout), 40001 (Deadlock), etc.
- **Max Retries:** Configurable (default: 3 attempts)
- **Backoff Strategy:** Exponential with configurable base delay (default: 1 second)
- **Formula:** `delay = retry_delay * (2 ** attempt)`

**Example:** With default settings (retry_delay=1s, max_retries=3):
- Attempt 1: Immediate
- Attempt 2: Wait 1s
- Attempt 3: Wait 2s
- Attempt 4: Wait 4s
- If all fail: Raise final error

**Configuration:** See [CONFIGURATION.md](CONFIGURATION.md) for `max_retries` and `retry_delay` settings.

---

## Security

### Read-Only Enforcement

MSSQL MCP Server enforces read-only access through multiple security layers:

1. **Query Prefix Check:** Only queries starting with `SELECT` are allowed
2. **Keyword Scanning:** Blocks dangerous keywords (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, EXEC, etc.)
3. **Word Boundary Detection:** Uses regex `\b{keyword}\b` to avoid false positives on column names like `updated_at`

### Security Best Practices

1. **Use Least Privilege:** Configure database user with SELECT-only permissions
2. **Network Isolation:** Run server in isolated network environment
3. **Connection Limits:** Configure `connection_timeout` to prevent resource exhaustion
4. **Query Limits:** Use `max_rows` parameter to prevent excessive data retrieval
5. **Audit Logging:** Enable SQL Server audit logging for compliance

### Windows Authentication

The server uses Windows Authentication (`Trusted_Connection=yes`) which provides:
- No credentials in configuration files
- Integration with Active Directory
- Support for Kerberos authentication
- Audit trail via Windows security logs

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for Windows Authentication setup guide.

---

## See Also

- [Configuration Guide](CONFIGURATION.md) - Server configuration options
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Examples](EXAMPLES.md) - Example queries and use cases
- [Development Guide](DEVELOPMENT.md) - Contributing to the project
