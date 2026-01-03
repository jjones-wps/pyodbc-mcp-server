# Configuration Guide

Complete guide to configuring MSSQL MCP Server including CLI arguments, configuration files, environment variables, and validation.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Priority](#configuration-priority)
- [Configuration Methods](#configuration-methods)
  - [CLI Arguments](#cli-arguments)
  - [TOML Configuration File](#toml-configuration-file)
  - [Environment Variables](#environment-variables)
- [Configuration Parameters](#configuration-parameters)
- [Validation](#validation)
- [Examples](#examples)
- [Migration Guide](#migration-guide)

---

## Quick Start

**Minimal setup with defaults:**
```bash
# Uses defaults: server=localhost, database=master, Windows Authentication
mssql-mcp-server
```

**Using TOML config file:**
```bash
# Create config.toml from example
cp config.example.toml config.toml

# Edit config.toml with your settings
nano config.toml

# Run with config file
mssql-mcp-server --config config.toml
```

**Override specific settings:**
```bash
# Use config file but override database
mssql-mcp-server --config config.toml --database AdventureWorks
```

---

## Configuration Priority

Configuration values are merged from multiple sources with the following priority (highest to lowest):

```
1. CLI Arguments          (highest priority)
        ↓
2. Config File (--config)
        ↓
3. Environment Variables
        ↓
4. Defaults              (lowest priority)
```

**Example:**
```bash
# Environment variable sets database to "master"
export MSSQL_DATABASE="master"

# Config file sets database to "AdventureWorks"
# config.toml: database = "AdventureWorks"

# CLI argument sets database to "Production"
mssql-mcp-server --config config.toml --database Production

# Result: database = "Production" (CLI wins)
```

---

## Configuration Methods

### CLI Arguments

Run server with command-line arguments for quick configuration.

**Syntax:**
```bash
mssql-mcp-server [OPTIONS]
```

**Available Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--server` | string | SQL Server hostname or IP address |
| `--database` | string | Target database name |
| `--driver` | string | ODBC driver name |
| `--connection-timeout` | int | Connection timeout in seconds (1-300) |
| `--query-timeout` | int | Query execution timeout in seconds (1-3600) |
| `--max-retries` | int | Max retry attempts for transient errors (0-10) |
| `--retry-delay` | float | Base retry delay in seconds (0-60) |
| `--config` | path | Path to TOML configuration file |
| `--validate-only` | flag | Validate configuration and exit (no server start) |

**Example:**
```bash
mssql-mcp-server \
  --server sql.example.com \
  --database AdventureWorks \
  --connection-timeout 60 \
  --query-timeout 120 \
  --max-retries 5
```

**Validation Mode:**
```bash
# Check configuration without starting server
mssql-mcp-server --config config.toml --validate-only

# Output:
# ✓ Configuration is valid
#   Server: localhost
#   Database: master
#   Driver: ODBC Driver 17 for SQL Server
#   Connection Timeout: 30s
```

---

### TOML Configuration File

TOML configuration files provide persistent, version-controlled configuration.

**File Format:**
```toml
[mssql]
# SQL Server connection settings
server = "localhost"
database = "master"
driver = "ODBC Driver 17 for SQL Server"

# Timeout settings (in seconds)
connection_timeout = 30  # Max: 300 (5 minutes)
query_timeout = 30       # Max: 3600 (1 hour)

# Retry settings for transient errors
max_retries = 3          # Max: 10
retry_delay = 1.0        # Max: 60.0 (seconds)
```

**Usage:**
```bash
# Specify config file path
mssql-mcp-server --config /path/to/config.toml

# Relative path from current directory
mssql-mcp-server --config ./config.toml

# Override specific settings from config file
mssql-mcp-server --config config.toml --server production-sql.example.com
```

**Best Practices:**
1. **Use `config.example.toml` as template** - Never commit actual credentials
2. **Version control config structure** - Commit `config.example.toml`, not `config.toml`
3. **Store sensitive configs outside repo** - Use absolute paths for production configs
4. **Document environment-specific configs** - Comment your settings

**Example Production Config:**
```toml
# production.toml - Production SQL Server configuration
[mssql]
server = "prod-sql01.contoso.com"
database = "ERP_Production"
driver = "ODBC Driver 18 for SQL Server"

# Higher timeouts for production workload
connection_timeout = 60
query_timeout = 120

# Aggressive retry for production reliability
max_retries = 5
retry_delay = 2.0
```

---

### Environment Variables

Environment variables provide configuration without files (useful for containers, CI/CD).

**Supported Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SERVER` | `localhost` | SQL Server hostname |
| `MSSQL_DATABASE` | `master` | Target database |
| `ODBC_DRIVER` | `ODBC Driver 17 for SQL Server` | ODBC driver name |
| `MSSQL_CONNECTION_TIMEOUT` | `30` | Connection timeout (seconds) |
| `MSSQL_QUERY_TIMEOUT` | `30` | Query timeout (seconds) |
| `MSSQL_MAX_RETRIES` | `3` | Max retry attempts |
| `MSSQL_RETRY_DELAY` | `1.0` | Base retry delay (seconds) |

**Example (Linux/macOS):**
```bash
export MSSQL_SERVER="sql.example.com"
export MSSQL_DATABASE="AdventureWorks"
export MSSQL_CONNECTION_TIMEOUT="60"
export MSSQL_QUERY_TIMEOUT="120"

# Run server (will use environment variables)
mssql-mcp-server
```

**Example (Windows PowerShell):**
```powershell
$env:MSSQL_SERVER = "sql.example.com"
$env:MSSQL_DATABASE = "AdventureWorks"
$env:MSSQL_CONNECTION_TIMEOUT = "60"
$env:MSSQL_QUERY_TIMEOUT = "120"

# Run server
mssql-mcp-server
```

**Example (Docker):**
```bash
docker run -d \
  -e MSSQL_SERVER=sql.example.com \
  -e MSSQL_DATABASE=AdventureWorks \
  -e MSSQL_CONNECTION_TIMEOUT=60 \
  -e MSSQL_QUERY_TIMEOUT=120 \
  mssql-mcp-server
```

**Example (.env file):**
```bash
# .env - Local development configuration
MSSQL_SERVER=localhost
MSSQL_DATABASE=AdventureWorks_Dev
ODBC_DRIVER=ODBC Driver 17 for SQL Server
MSSQL_CONNECTION_TIMEOUT=30
MSSQL_QUERY_TIMEOUT=30
MSSQL_MAX_RETRIES=3
MSSQL_RETRY_DELAY=1.0
```

```bash
# Load .env and run server
source .env
mssql-mcp-server
```

---

## Configuration Parameters

### Server Connection Parameters

#### server
**Type:** string
**Default:** `localhost`
**Description:** SQL Server hostname or IP address

**Examples:**
```toml
server = "localhost"                    # Local instance
server = "sql.example.com"              # Remote server
server = "192.168.1.100"                # IP address
server = "sql.example.com,1433"         # Custom port
server = "localhost\\SQLEXPRESS"        # Named instance
```

**Validation:**
- Cannot be empty
- Must be a valid hostname or IP address

---

#### database
**Type:** string
**Default:** `master`
**Description:** Target database name

**Examples:**
```toml
database = "master"           # System database
database = "AdventureWorks"   # User database
database = "ERP_Production"   # Production database
```

**Validation:**
- Cannot be empty
- Must exist on the server (validated at startup)

---

#### driver
**Type:** string
**Default:** `ODBC Driver 17 for SQL Server`
**Description:** ODBC driver name (must be installed)

**Common Drivers:**
```toml
driver = "ODBC Driver 17 for SQL Server"  # Most common
driver = "ODBC Driver 18 for SQL Server"  # Newer version
driver = "SQL Server"                     # Legacy driver (not recommended)
```

**Validation:**
- Cannot be empty
- Must be installed on the system (see [TROUBLESHOOTING.md](TROUBLESHOOTING.md))

**Check installed drivers:**
```bash
# Windows PowerShell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}

# Linux
odbcinst -q -d | grep -i "sql server"

# macOS
odbcinst -q -d | grep -i "sql server"
```

---

### Timeout Parameters

#### connection_timeout
**Type:** integer
**Default:** `30`
**Range:** 1-300 seconds (5 minutes max)
**Description:** Maximum time to wait for database connection

**Examples:**
```toml
connection_timeout = 15   # Fast fail for local servers
connection_timeout = 30   # Default (balanced)
connection_timeout = 60   # Slow networks or remote servers
```

**When to increase:**
- Slow network connections
- VPN or remote access
- Server under heavy load
- Initial connection takes long

**When to decrease:**
- Fast local connections
- Quick failure detection desired
- Load balancing with multiple servers

---

#### query_timeout
**Type:** integer
**Default:** `30`
**Range:** 1-3600 seconds (1 hour max)
**Description:** Maximum time for query execution

**Examples:**
```toml
query_timeout = 30    # Default for OLTP queries
query_timeout = 120   # Complex analytical queries
query_timeout = 300   # Long-running reports (5 minutes)
query_timeout = 600   # Data warehouse queries (10 minutes)
```

**Considerations:**
- OLTP queries: 5-30 seconds
- Reports: 60-300 seconds
- Analytics: 300-600 seconds
- ETL/Data loads: 600-3600 seconds

**Note:** Queries exceeding this timeout will be terminated and return a `TIMEOUT_ERROR`.

---

### Retry Parameters

#### max_retries
**Type:** integer
**Default:** `3`
**Range:** 0-10 attempts
**Description:** Maximum retry attempts for transient database errors

**Examples:**
```toml
max_retries = 0   # No retries (fail immediately)
max_retries = 3   # Default (moderate resilience)
max_retries = 5   # Production (high resilience)
max_retries = 10  # Maximum allowed
```

**Transient Errors (auto-retry):**
- `08S01` - Communication link failure
- `08001` - Connection failure
- `HYT00` - Timeout expired
- `HYT01` - Connection timeout
- `40001` - Deadlock detected
- `40197` - Service unavailable
- `40501` - Service busy
- `40613` - Database unavailable

**Non-Transient Errors (no retry):**
- `42000` - Syntax error
- `42S02` - Object not found
- `S0001` - Permission denied

---

#### retry_delay
**Type:** float
**Default:** `1.0`
**Range:** 0.0-60.0 seconds
**Description:** Base delay for exponential backoff (delay = retry_delay * 2^attempt)

**Examples:**
```toml
retry_delay = 0.5   # Fast retry (0.5s, 1s, 2s, 4s)
retry_delay = 1.0   # Default (1s, 2s, 4s, 8s)
retry_delay = 2.0   # Slower retry (2s, 4s, 8s, 16s)
```

**Backoff Calculation:**
```
Attempt 1: Immediate (no delay)
Attempt 2: retry_delay * (2^1) = retry_delay * 2
Attempt 3: retry_delay * (2^2) = retry_delay * 4
Attempt 4: retry_delay * (2^3) = retry_delay * 8
```

**Example with retry_delay=1.0, max_retries=3:**
```
Attempt 1: Execute immediately
Attempt 2: Wait 1s, then execute
Attempt 3: Wait 2s, then execute
Attempt 4: Wait 4s, then execute
If all fail: Raise error
```

---

## Validation

### Automatic Validation

Configuration is automatically validated at startup with helpful error messages:

**Example (invalid query_timeout):**
```bash
$ mssql-mcp-server --query-timeout 5000

Configuration validation failed:
  - Query timeout too large (got 5000, max 3600)
```

**Example (empty server):**
```bash
$ mssql-mcp-server --server ""

Configuration validation failed:
  - Server name cannot be empty
```

### Manual Validation

Use `--validate-only` flag to check configuration without starting the server:

```bash
# Validate config file
mssql-mcp-server --config config.toml --validate-only

# Validate environment variables
export MSSQL_SERVER="sql.example.com"
mssql-mcp-server --validate-only

# Validate CLI arguments
mssql-mcp-server --server localhost --database master --validate-only
```

**Success Output:**
```
✓ Configuration is valid
  Server: localhost
  Database: master
  Driver: ODBC Driver 17 for SQL Server
  Connection Timeout: 30s
```

**Failure Output:**
```
Configuration validation failed:
  - Query timeout must be positive (got -5)
  - Max retries too large (got 20, max 10)
```

### Validation Rules

| Parameter | Validation Rule |
|-----------|----------------|
| `server` | Non-empty string |
| `database` | Non-empty string |
| `driver` | Non-empty string |
| `connection_timeout` | 1 ≤ value ≤ 300 |
| `query_timeout` | 1 ≤ value ≤ 3600 |
| `max_retries` | 0 ≤ value ≤ 10 |
| `retry_delay` | 0.0 ≤ value ≤ 60.0 |

---

## Examples

### Local Development

**config.toml:**
```toml
[mssql]
server = "localhost"
database = "AdventureWorks_Dev"
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 30
query_timeout = 30
max_retries = 3
retry_delay = 1.0
```

```bash
mssql-mcp-server --config config.toml
```

---

### Production (High Availability)

**production.toml:**
```toml
[mssql]
server = "prod-sql01.contoso.com"
database = "ERP_Production"
driver = "ODBC Driver 18 for SQL Server"

# Higher timeouts for production workload
connection_timeout = 60
query_timeout = 300

# Aggressive retry for high availability
max_retries = 5
retry_delay = 2.0
```

```bash
mssql-mcp-server --config production.toml
```

---

### Named Instance

**config.toml:**
```toml
[mssql]
server = "localhost\\SQLEXPRESS"
database = "TestDB"
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 30
query_timeout = 30
max_retries = 3
retry_delay = 1.0
```

---

### Custom Port

**config.toml:**
```toml
[mssql]
server = "sql.example.com,1434"  # Custom port
database = "AdventureWorks"
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 30
query_timeout = 30
max_retries = 3
retry_delay = 1.0
```

---

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  mssql-mcp-server:
    image: mssql-mcp-server:latest
    environment:
      - MSSQL_SERVER=sqlserver
      - MSSQL_DATABASE=AdventureWorks
      - MSSQL_CONNECTION_TIMEOUT=60
      - MSSQL_QUERY_TIMEOUT=120
      - MSSQL_MAX_RETRIES=5
      - MSSQL_RETRY_DELAY=2.0
    depends_on:
      - sqlserver

  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=YourStrongPassword123
```

---

### Kubernetes ConfigMap

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mssql-mcp-config
data:
  config.toml: |
    [mssql]
    server = "sql.production.svc.cluster.local"
    database = "ApplicationDB"
    driver = "ODBC Driver 18 for SQL Server"
    connection_timeout = 60
    query_timeout = 300
    max_retries = 5
    retry_delay = 2.0
```

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mssql-mcp-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: server
        image: mssql-mcp-server:latest
        command: ["mssql-mcp-server", "--config", "/config/config.toml"]
        volumeMounts:
        - name: config
          mountPath: /config
      volumes:
      - name: config
        configMap:
          name: mssql-mcp-config
```

---

## Migration Guide

### From Environment Variables to Config File

**Before (environment variables):**
```bash
export MSSQL_SERVER="sql.example.com"
export MSSQL_DATABASE="AdventureWorks"
export MSSQL_CONNECTION_TIMEOUT="60"
export MSSQL_QUERY_TIMEOUT="120"

mssql-mcp-server
```

**After (TOML config file):**
```toml
# config.toml
[mssql]
server = "sql.example.com"
database = "AdventureWorks"
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 60
query_timeout = 120
max_retries = 3
retry_delay = 1.0
```

```bash
mssql-mcp-server --config config.toml
```

**Benefits:**
- Version control configuration
- Easier to document and share
- No shell-specific syntax
- Better for complex configurations

---

### From CLI Arguments to Config File

**Before (CLI arguments):**
```bash
mssql-mcp-server \
  --server sql.example.com \
  --database AdventureWorks \
  --connection-timeout 60 \
  --query-timeout 120 \
  --max-retries 5 \
  --retry-delay 2.0
```

**After (TOML config file):**
```toml
# config.toml
[mssql]
server = "sql.example.com"
database = "AdventureWorks"
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 60
query_timeout = 120
max_retries = 5
retry_delay = 2.0
```

```bash
mssql-mcp-server --config config.toml
```

**Benefits:**
- Cleaner command line
- Easier to maintain
- Can comment settings
- Better for CI/CD

---

### Hybrid Approach (Recommended for CI/CD)

Use config files for static settings, environment variables for secrets, and CLI for overrides:

**config.toml (version controlled):**
```toml
[mssql]
# Static configuration (no secrets)
driver = "ODBC Driver 17 for SQL Server"
connection_timeout = 60
query_timeout = 120
max_retries = 5
retry_delay = 2.0
```

**Environment variables (secrets):**
```bash
export MSSQL_SERVER="prod-sql.example.com"
export MSSQL_DATABASE="Production"
```

**CLI (environment-specific overrides):**
```bash
# Development
mssql-mcp-server --config config.toml --database AdventureWorks_Dev

# Staging
mssql-mcp-server --config config.toml --database AdventureWorks_Staging

# Production
mssql-mcp-server --config config.toml --database AdventureWorks_Production
```

---

## See Also

- [API Reference](API.md) - Tool and resource documentation
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common configuration issues
- [Examples](EXAMPLES.md) - Example queries and use cases
- [Development Guide](DEVELOPMENT.md) - Contributing to the project
