# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with MSSQL MCP Server.

## Table of Contents

- [Connection Issues](#connection-issues)
  - [Cannot Connect to SQL Server](#cannot-connect-to-sql-server)
  - [Connection Timeout](#connection-timeout)
  - [Windows Authentication Failed](#windows-authentication-failed)
  - [Named Instance Not Found](#named-instance-not-found)
- [Driver Issues](#driver-issues)
  - [ODBC Driver Not Found](#odbc-driver-not-found)
  - [Installing ODBC Drivers](#installing-odbc-drivers)
  - [Driver Version Mismatch](#driver-version-mismatch)
- [Query Issues](#query-issues)
  - [Query Timeout](#query-timeout)
  - [Permission Denied](#permission-denied)
  - [Syntax Errors](#syntax-errors)
  - [Object Not Found](#object-not-found)
- [Security Issues](#security-issues)
  - [Blocked Keywords](#blocked-keywords)
  - [Non-SELECT Query Rejected](#non-select-query-rejected)
- [Performance Issues](#performance-issues)
  - [Slow Queries](#slow-queries)
  - [Connection Pool Exhaustion](#connection-pool-exhaustion)
- [Configuration Issues](#configuration-issues)
  - [Configuration Validation Errors](#configuration-validation-errors)
  - [TOML Parse Errors](#toml-parse-errors)
- [Network Issues](#network-issues)
  - [Firewall Blocking Connection](#firewall-blocking-connection)
  - [VPN Connection Issues](#vpn-connection-issues)
- [Diagnostics](#diagnostics)
  - [Enable Logging](#enable-logging)
  - [Test Connection](#test-connection)
  - [Verify Driver Installation](#verify-driver-installation)

---

## Connection Issues

### Cannot Connect to SQL Server

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [08001] [Microsoft][ODBC Driver 17 for SQL Server]Named Pipes Provider: Could not open a connection to SQL Server",
  "details": {
    "server": "localhost",
    "database": "master",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Possible Causes:**
1. SQL Server service not running
2. Incorrect server name or hostname
3. SQL Server not listening on TCP/IP
4. Firewall blocking connection
5. SQL Server Browser service not running (for named instances)

**Solutions:**

**1. Verify SQL Server is running:**

Windows:
```powershell
# Check SQL Server service status
Get-Service MSSQLSERVER

# Start SQL Server if stopped
Start-Service MSSQLSERVER
```

Linux (SQL Server on Linux):
```bash
# Check status
sudo systemctl status mssql-server

# Start SQL Server
sudo systemctl start mssql-server
```

**2. Test TCP/IP connectivity:**

```bash
# Test if SQL Server is listening (default port 1433)
telnet localhost 1433

# Or use netcat
nc -zv localhost 1433

# Or PowerShell
Test-NetConnection -ComputerName localhost -Port 1433
```

**3. Enable TCP/IP protocol:**

Open SQL Server Configuration Manager:
1. Navigate to SQL Server Network Configuration > Protocols for [Instance Name]
2. Right-click TCP/IP → Enable
3. Restart SQL Server service

**4. Check SQL Server error logs:**

```sql
-- View SQL Server error log
EXEC sp_readerrorlog 0, 1
```

---

### Connection Timeout

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [HYT00] [Microsoft][ODBC Driver 17 for SQL Server]Login timeout expired",
  "details": {
    "server": "sql.example.com",
    "database": "AdventureWorks",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Possible Causes:**
1. Network latency
2. Server overloaded
3. Slow DNS resolution
4. Connection timeout too short

**Solutions:**

**1. Increase connection timeout:**

```bash
# CLI
mssql-mcp-server --server sql.example.com --connection-timeout 60

# Config file
# config.toml
[mssql]
server = "sql.example.com"
connection_timeout = 60  # Increase from 30 to 60 seconds
```

**2. Test network latency:**

```bash
# Test DNS resolution
nslookup sql.example.com

# Test ping
ping sql.example.com

# Test traceroute (Windows)
tracert sql.example.com

# Test traceroute (Linux/macOS)
traceroute sql.example.com
```

**3. Use IP address instead of hostname:**

```toml
# config.toml
[mssql]
server = "192.168.1.100"  # Use IP to bypass DNS
```

---

### Windows Authentication Failed

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [28000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Login failed for user 'DOMAIN\\User'",
  "details": {
    "server": "localhost",
    "database": "master",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Possible Causes:**
1. User account not in SQL Server login list
2. SQL Server using SQL Server Authentication only
3. Kerberos authentication issues
4. User account disabled or locked

**Solutions:**

**1. Verify SQL Server authentication mode:**

```sql
-- Check authentication mode (1 = Windows, 2 = Mixed)
SELECT SERVERPROPERTY('IsIntegratedSecurityOnly') AS AuthenticationMode
```

**2. Add Windows user to SQL Server:**

```sql
-- Create login for Windows user
CREATE LOGIN [DOMAIN\User] FROM WINDOWS

-- Grant database access
USE AdventureWorks
CREATE USER [DOMAIN\User] FOR LOGIN [DOMAIN\User]

-- Grant read permissions
ALTER ROLE db_datareader ADD MEMBER [DOMAIN\User]
```

**3. Verify Windows user:**

```powershell
# Check current user
whoami

# Test SQL Server access
sqlcmd -S localhost -E -Q "SELECT SUSER_NAME()"
```

**4. Enable Mixed Mode Authentication (if needed):**

SQL Server Configuration Manager:
1. Right-click SQL Server instance → Properties
2. Security tab → SQL Server and Windows Authentication mode
3. Restart SQL Server service

**Note:** MSSQL MCP Server uses Windows Authentication only. Mixed mode is only needed for SQL logins.

---

### Named Instance Not Found

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [08001] [Microsoft][ODBC Driver 17 for SQL Server]SQL Server Network Interfaces: Error Locating Server/Instance Specified",
  "details": {
    "server": "localhost\\SQLEXPRESS",
    "database": "master",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Possible Causes:**
1. SQL Server Browser service not running
2. Incorrect instance name
3. UDP port 1434 blocked

**Solutions:**

**1. Start SQL Server Browser service:**

Windows:
```powershell
# Check status
Get-Service SQLBrowser

# Start service
Start-Service SQLBrowser

# Set to auto-start
Set-Service SQLBrowser -StartupType Automatic
```

**2. Verify instance name:**

```powershell
# List SQL Server instances
Get-Service | Where-Object {$_.Name -like "MSSQL*"}

# Example output:
# MSSQLSERVER      (default instance)
# MSSQL$SQLEXPRESS (named instance)
```

**3. Use server,port format instead:**

```toml
# config.toml
[mssql]
# Instead of: server = "localhost\\SQLEXPRESS"
# Use port directly:
server = "localhost,1433"  # Replace 1433 with actual port
```

**4. Find SQL Server instance port:**

```sql
-- Run on SQL Server
SELECT local_net_address, local_tcp_port
FROM sys.dm_exec_connections
WHERE session_id = @@SPID
```

---

## Driver Issues

### ODBC Driver Not Found

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [IM002] [Microsoft][ODBC Driver Manager] Data source name not found and no default driver specified",
  "details": {
    "server": "localhost",
    "database": "master",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Possible Causes:**
1. ODBC driver not installed
2. Incorrect driver name in configuration
3. Driver name mismatch (version, architecture)

**Solutions:**

**1. List installed ODBC drivers:**

Windows PowerShell:
```powershell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"} | Select-Object Name
```

Linux:
```bash
odbcinst -q -d | grep -i "sql server"
```

macOS:
```bash
odbcinst -q -d | grep -i "sql server"
```

**2. Install ODBC driver (see [Installing ODBC Drivers](#installing-odbc-drivers))**

**3. Update configuration with correct driver name:**

```toml
# config.toml
[mssql]
# Use exact name from installed drivers list
driver = "ODBC Driver 17 for SQL Server"  # Most common
# driver = "ODBC Driver 18 for SQL Server"  # Newer version
# driver = "SQL Server"                     # Legacy (not recommended)
```

---

### Installing ODBC Drivers

#### Windows

**Download and Install:**
1. Download from [Microsoft ODBC Driver Download Page](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. Run installer (msodbcsql.msi)
3. Follow installation wizard
4. Verify installation:

```powershell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
```

**Recommended Driver:** ODBC Driver 17 for SQL Server

---

#### Ubuntu/Debian Linux

```bash
# Add Microsoft repository
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Update package list
sudo apt-get update

# Install ODBC Driver 17
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Install development headers (optional)
sudo ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev

# Verify installation
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"
```

---

#### Red Hat/CentOS Linux

```bash
# Add Microsoft repository
sudo curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo

# Install ODBC Driver 17
sudo ACCEPT_EULA=Y yum install -y msodbcsql17

# Install development tools (optional)
sudo ACCEPT_EULA=Y yum install -y mssql-tools unixODBC-devel

# Verify installation
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"
```

---

#### macOS

```bash
# Install via Homebrew
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql17 mssql-tools

# Verify installation
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"
```

---

### Driver Version Mismatch

**Error Message:**
```
Configuration validation failed:
  - ODBC driver name cannot be empty
```

**Problem:** Configuration specifies wrong driver version

**Solution:**

**1. Check installed drivers:**

```bash
# Windows
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}

# Linux/macOS
odbcinst -q -d | grep -i "sql server"
```

**2. Update configuration:**

```toml
# config.toml
[mssql]
# Use exact name from installed drivers
driver = "ODBC Driver 17 for SQL Server"  # Not "ODBC Driver 17"
```

---

## Query Issues

### Query Timeout

**Error Message:**
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

**Possible Causes:**
1. Slow query (missing indexes, full table scan)
2. Large result set
3. Server under heavy load
4. Timeout too short for complex queries

**Solutions:**

**1. Increase query timeout:**

```bash
# CLI
mssql-mcp-server --query-timeout 120

# Config file
# config.toml
[mssql]
query_timeout = 120  # Increase from 30 to 120 seconds
```

**2. Optimize query:**

```sql
-- Add indexes to improve performance
CREATE NONCLUSTERED INDEX IX_Users_Email ON Users(Email)

-- Use TOP to limit results
SELECT TOP 1000 * FROM LargeTable

-- Check execution plan
SET SHOWPLAN_ALL ON
SELECT * FROM SlowTable
SET SHOWPLAN_ALL OFF
```

**3. Use max_rows parameter to limit results:**

```python
# Limit to 100 rows (default)
result = await ReadData("SELECT * FROM LargeTable")

# Increase limit
result = await ReadData("SELECT * FROM LargeTable", max_rows=1000)
```

**4. Identify slow queries:**

```sql
-- Find top 10 slowest queries
SELECT TOP 10
    qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time,
    qs.execution_count,
    SUBSTRING(qt.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset
          WHEN -1 THEN DATALENGTH(qt.text)
          ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2) + 1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
ORDER BY avg_elapsed_time DESC
```

---

### Permission Denied

**Error Message:**
```json
{
  "error": "QUERY_ERROR",
  "message": "Query failed: [42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]The SELECT permission was denied on the object 'SensitiveTable', database 'AdventureWorks', schema 'dbo'",
  "details": {
    "query": "SELECT * FROM dbo.SensitiveTable",
    "error_code": "42000"
  }
}
```

**Possible Causes:**
1. User lacks SELECT permission on table
2. User not member of required database role
3. Row-level security blocking access
4. Dynamic data masking applied

**Solutions:**

**1. Grant SELECT permission:**

```sql
-- Grant SELECT on specific table
GRANT SELECT ON dbo.SensitiveTable TO [DOMAIN\User]

-- Grant SELECT on all tables in schema
GRANT SELECT ON SCHEMA::dbo TO [DOMAIN\User]

-- Add user to db_datareader role (all tables)
ALTER ROLE db_datareader ADD MEMBER [DOMAIN\User]
```

**2. Verify current permissions:**

```sql
-- Check permissions for current user
SELECT * FROM fn_my_permissions('dbo.SensitiveTable', 'OBJECT')

-- Check database role membership
SELECT
    dp.name AS DatabaseRole,
    dp2.name AS MemberName
FROM sys.database_role_members drm
JOIN sys.database_principals dp ON drm.role_principal_id = dp.principal_id
JOIN sys.database_principals dp2 ON drm.member_principal_id = dp2.principal_id
WHERE dp2.name = CURRENT_USER
```

---

### Syntax Errors

**Error Message:**
```json
{
  "error": "QUERY_ERROR",
  "message": "Query failed: [42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Incorrect syntax near 'FROM'",
  "details": {
    "query": "SELECT FROM Users",
    "error_code": "42000"
  }
}
```

**Possible Causes:**
1. Invalid SQL syntax
2. Typo in query
3. Missing column list in SELECT
4. Reserved keyword used without brackets

**Solutions:**

**1. Fix SQL syntax:**

```sql
-- Before (error)
SELECT FROM Users

-- After (correct)
SELECT * FROM Users
SELECT UserId, Username FROM Users
```

**2. Escape reserved keywords:**

```sql
-- Before (error - "Order" is reserved keyword)
SELECT * FROM Order

-- After (correct)
SELECT * FROM [Order]
```

**3. Test query in SQL Server Management Studio first**

**4. Use query validation:**

```sql
-- Validate without executing
SET PARSEONLY ON
SELECT * FROM Users
SET PARSEONLY OFF
```

---

### Object Not Found

**Error Message:**
```json
{
  "error": "QUERY_ERROR",
  "message": "Query failed: [42S02] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Invalid object name 'Users'",
  "details": {
    "query": "SELECT * FROM Users",
    "error_code": "42S02"
  }
}
```

**Possible Causes:**
1. Table doesn't exist
2. Wrong database selected
3. Missing schema qualifier
4. Case-sensitive collation

**Solutions:**

**1. List available tables:**

```python
# Use ListTables tool
result = await ListTables()
```

**2. Use schema-qualified names:**

```sql
-- Before (may fail if default schema not dbo)
SELECT * FROM Users

-- After (explicit schema)
SELECT * FROM dbo.Users
```

**3. Check database context:**

```sql
-- Verify current database
SELECT DB_NAME()

-- Switch database
USE AdventureWorks
```

**4. Search for table:**

```sql
-- Find tables by name pattern
SELECT
    SCHEMA_NAME(schema_id) AS schema_name,
    name AS table_name
FROM sys.tables
WHERE name LIKE '%User%'
```

---

## Security Issues

### Blocked Keywords

**Error Message:**
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
- INSERT, UPDATE, DELETE, MERGE
- DROP, CREATE, ALTER, TRUNCATE
- EXEC, EXECUTE, sp_executesql
- xp_cmdshell, OPENROWSET, OPENDATASOURCE
- BACKUP, RESTORE
- GRANT, REVOKE, DENY

**Solution:**

**1. Use SELECT queries only:**

```sql
-- Before (blocked)
DELETE FROM Users WHERE UserId = 1

-- After (read-only alternative)
SELECT * FROM Users WHERE UserId = 1
```

**2. For administrative tasks, connect directly to SQL Server:**

```powershell
# Use sqlcmd for write operations
sqlcmd -S localhost -E -Q "DELETE FROM Users WHERE UserId = 1"
```

**Note:** MSSQL MCP Server is intentionally read-only for security. Write operations must be performed through direct SQL Server connections.

---

### Non-SELECT Query Rejected

**Error Message:**
```json
{
  "error": "SECURITY_ERROR",
  "message": "Only SELECT queries are allowed. This server is read-only.",
  "details": {
    "query": "INSERT INTO Users (Username) VALUES ('alice')",
    "blocked_keyword": "non-SELECT statement"
  }
}
```

**Solution:**

**1. Rewrite query as SELECT:**

```sql
-- Before (blocked)
INSERT INTO Users (Username) VALUES ('alice')

-- After (view what would be inserted)
SELECT 'alice' AS Username
```

**2. Use CTE for complex queries:**

```sql
-- Common Table Expression (CTE) for analysis
WITH RecentOrders AS (
    SELECT OrderId, CustomerId, OrderDate
    FROM Orders
    WHERE OrderDate > DATEADD(DAY, -30, GETDATE())
)
SELECT * FROM RecentOrders
```

---

## Performance Issues

### Slow Queries

**Symptoms:**
- Queries taking longer than expected
- Timeout errors
- High CPU or memory usage

**Diagnostics:**

**1. Check query execution plan:**

```sql
-- Enable actual execution plan
SET STATISTICS XML ON
SELECT * FROM LargeTable WHERE Column1 = 'value'
SET STATISTICS XML OFF
```

**2. Check for missing indexes:**

```sql
-- Find missing indexes
SELECT
    migs.avg_total_user_cost * (migs.avg_user_impact / 100.0) * (migs.user_seeks + migs.user_scans) AS improvement_measure,
    'CREATE INDEX IX_' + OBJECT_NAME(mid.object_id) + '_' + REPLACE(REPLACE(REPLACE(mid.equality_columns, ', ', '_'), '[', ''), ']', '') +
    ' ON ' + mid.statement + ' (' + ISNULL(mid.equality_columns, '') +
    CASE WHEN mid.equality_columns IS NOT NULL AND mid.inequality_columns IS NOT NULL THEN ',' ELSE '' END +
    ISNULL(mid.inequality_columns, '') + ')' +
    ISNULL(' INCLUDE (' + mid.included_columns + ')', '') AS create_index_statement
FROM sys.dm_db_missing_index_groups mig
INNER JOIN sys.dm_db_missing_index_group_stats migs ON migs.group_handle = mig.index_group_handle
INNER JOIN sys.dm_db_missing_index_details mid ON mig.index_handle = mid.index_handle
ORDER BY improvement_measure DESC
```

**Solutions:**

**1. Create indexes:**

```sql
-- Add index on frequently queried columns
CREATE NONCLUSTERED INDEX IX_Users_Email ON Users(Email)

-- Composite index for multi-column WHERE clauses
CREATE NONCLUSTERED INDEX IX_Orders_Customer_Date ON Orders(CustomerId, OrderDate)
```

**2. Update statistics:**

```sql
-- Update statistics for better query plans
UPDATE STATISTICS Users WITH FULLSCAN
```

**3. Rewrite query to avoid full table scans:**

```sql
-- Before (full table scan)
SELECT * FROM Orders WHERE YEAR(OrderDate) = 2025

-- After (index seek)
SELECT * FROM Orders WHERE OrderDate >= '2025-01-01' AND OrderDate < '2026-01-01'
```

**4. Use appropriate max_rows:**

```python
# Limit results for performance
result = await ReadData("SELECT * FROM LargeTable", max_rows=100)
```

---

### Connection Pool Exhaustion

**Symptom:** Connection errors during high concurrent load

**Note:** Current version creates new connection per request (no pooling).

**Solution:**

Monitor connection count:

```sql
-- Check active connections
SELECT
    DB_NAME(dbid) AS DatabaseName,
    COUNT(dbid) AS NumberOfConnections,
    loginame AS LoginName
FROM sys.sysprocesses
WHERE dbid > 0
GROUP BY dbid, loginame
```

**Workaround:** Limit concurrent requests at application level.

**Future:** Connection pooling planned for future version (see ROADMAP.md).

---

## Configuration Issues

### Configuration Validation Errors

**Error Message:**
```
Configuration validation failed:
  - Query timeout must be positive (got -5)
  - Max retries too large (got 20, max 10)
```

**Solution:**

**1. Check parameter ranges:**

| Parameter | Range |
|-----------|-------|
| connection_timeout | 1-300 seconds |
| query_timeout | 1-3600 seconds |
| max_retries | 0-10 attempts |
| retry_delay | 0.0-60.0 seconds |

**2. Fix configuration:**

```toml
# config.toml (BEFORE - invalid)
[mssql]
connection_timeout = -5   # Invalid: negative
query_timeout = 5000      # Invalid: > 3600
max_retries = 20          # Invalid: > 10
retry_delay = 100.0       # Invalid: > 60.0

# config.toml (AFTER - valid)
[mssql]
connection_timeout = 30
query_timeout = 120
max_retries = 5
retry_delay = 2.0
```

**3. Validate configuration:**

```bash
mssql-mcp-server --config config.toml --validate-only
```

---

### TOML Parse Errors

**Error Message:**
```
Failed to load config file: Expected '=' after a key in a key/value pair at line 5
```

**Common TOML Syntax Errors:**

**1. Missing equals sign:**

```toml
# Before (error)
[mssql]
server localhost

# After (correct)
[mssql]
server = "localhost"
```

**2. Unquoted strings:**

```toml
# Before (error)
server = localhost

# After (correct)
server = "localhost"
```

**3. Wrong number format:**

```toml
# Before (error)
connection_timeout = "30"  # String instead of number

# After (correct)
connection_timeout = 30
```

**4. Invalid section name:**

```toml
# Before (error)
[mssql-config]  # Hyphen not recommended in section name

# After (correct)
[mssql]
```

**Solution:**

Use `config.example.toml` as template:

```bash
cp config.example.toml config.toml
# Edit config.toml
```

---

## Network Issues

### Firewall Blocking Connection

**Error Message:**
```json
{
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to SQL Server: [08001] [Microsoft][ODBC Driver 17 for SQL Server]TCP Provider: No connection could be made because the target machine actively refused it",
  "details": {
    "server": "sql.example.com",
    "database": "master",
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

**Solution:**

**1. Check Windows Firewall (SQL Server host):**

```powershell
# Check firewall rule for SQL Server
Get-NetFirewallRule -DisplayName "*SQL*" | Select-Object DisplayName, Enabled

# Create firewall rule for SQL Server (default instance)
New-NetFirewallRule -DisplayName "SQL Server" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow

# Create firewall rule for SQL Server Browser (named instances)
New-NetFirewallRule -DisplayName "SQL Browser" -Direction Inbound -Protocol UDP -LocalPort 1434 -Action Allow
```

**2. Check Linux firewall:**

```bash
# Check firewalld (RHEL/CentOS)
sudo firewall-cmd --list-ports

# Add SQL Server port
sudo firewall-cmd --permanent --add-port=1433/tcp
sudo firewall-cmd --reload

# Check UFW (Ubuntu)
sudo ufw status

# Add SQL Server port
sudo ufw allow 1433/tcp
```

---

### VPN Connection Issues

**Symptom:** Connection works locally but fails over VPN

**Solution:**

**1. Test network connectivity:**

```bash
# Test ping
ping sql.example.com

# Test port
telnet sql.example.com 1433

# Or use PowerShell
Test-NetConnection -ComputerName sql.example.com -Port 1433
```

**2. Increase connection timeout for VPN:**

```toml
# config.toml
[mssql]
server = "sql.example.com"
connection_timeout = 60  # Increase for VPN latency
query_timeout = 120
```

**3. Use split tunneling if available:**

Configure VPN to route only SQL Server traffic through tunnel.

---

## Diagnostics

### Enable Logging

**Enable Python logging for debugging:**

```python
import logging

# Set logging level
logging.basicConfig(level=logging.DEBUG)

# Or set for specific module
logging.getLogger("mssql_mcp_server").setLevel(logging.DEBUG)
```

**Log locations:**

Windows:
```
%USERPROFILE%\AppData\Local\mssql-mcp-server\logs\
```

Linux/macOS:
```
~/.local/share/mssql-mcp-server/logs/
```

---

### Test Connection

**Use sqlcmd to test connection independently:**

Windows:
```powershell
# Test with Windows Authentication
sqlcmd -S localhost -E -Q "SELECT @@VERSION"

# Test with specific database
sqlcmd -S localhost -d AdventureWorks -E -Q "SELECT DB_NAME()"
```

Linux/macOS:
```bash
# Test connection
/opt/mssql-tools/bin/sqlcmd -S localhost -U sa -Q "SELECT @@VERSION"
```

---

### Verify Driver Installation

**Windows:**
```powershell
# List installed ODBC drivers
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL*"} | Format-Table Name, Platform, Version

# Test ODBC connection
Test-OdbcDriver -Name "ODBC Driver 17 for SQL Server"
```

**Linux/macOS:**
```bash
# List drivers
odbcinst -q -d

# Check specific driver
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"

# Test connection
isql -v DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=master;Trusted_Connection=yes
```

---

## See Also

- [API Reference](API.md) - Tool documentation
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Examples](EXAMPLES.md) - Example queries
- [Development Guide](DEVELOPMENT.md) - Contributing guide
