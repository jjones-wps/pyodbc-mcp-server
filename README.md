# pyodbc MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides **read-only** access to Microsoft SQL Server databases using **Windows Authentication**.

Built for environments where:
- 🔐 **Windows Authentication is required** (no username/password storage)
- 🛡️ **Read-only access is mandated** by IT security policy
- 🖥️ **SQL Server is accessed from Windows workstations**
- 🤖 **AI assistants need safe database access** (Claude Code, etc.)

## Features

- **Windows Authentication** - Uses `Trusted_Connection` via pyodbc, no credentials to manage
- **Read-only by design** - Only SELECT queries allowed, dangerous keywords blocked
- **Comprehensive error handling** - Typed exceptions with retry logic for transient failures
- **Row limiting** - Prevents accidental large result sets (configurable, max 10,000)
- **Schema exploration** - 10 tools for tables, views, indexes, constraints, relationships, and more
- **MCP resources** - 5 URI-based endpoints for quick data access
- **Configurable** - CLI arguments, TOML config files, or environment variables
- **Production-ready** - Query timeouts, connection retries, comprehensive logging

## Available Tools

| Tool | Description |
|------|-------------|
| `ListTables` | List all tables in the database, optionally filtered by schema |
| `DescribeTable` | Get detailed column definitions, primary keys, and foreign keys |
| `ReadData` | Execute SELECT queries with security filtering and row limits |
| `GetTableRelationships` | Find foreign key relationships with referential actions |
| `ListViews` | List all views in the database, optionally filtered by schema |
| `ListIndexes` | List all indexes for a specific table with metadata |
| `ListConstraints` | List all constraints (PK, FK, unique, check, default) |
| `ListStoredProcedures` | List all stored procedures, optionally filtered by schema |
| `ListFunctions` | List all user-defined functions, optionally filtered by schema |
| `ListTriggers` | List all triggers with table association and status |

**See [API Reference](docs/API.md) for complete documentation.**

## Installation

### Prerequisites

- Python 3.10+
- Windows with ODBC Driver 17+ for SQL Server
- Network access to your SQL Server
- Windows domain account with SELECT permissions on target database

### Install from PyPI

```bash
pip install pyodbc-mcp-server
```

### Install from Source

```bash
git clone https://github.com/jjones-wps/pyodbc-mcp-server.git
cd pyodbc-mcp-server
pip install -e .
```

### Install ODBC Driver (if needed)

Download and install [Microsoft ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

## Configuration

### Quick Configuration

The server supports three configuration methods (in priority order):

1. **CLI Arguments** (highest priority)
2. **TOML Configuration File**
3. **Environment Variables** (lowest priority)

**Minimal setup with defaults:**
```bash
mssql-mcp-server
```

**Using TOML config file:**
```bash
# Create config from example
cp config.example.toml config.toml

# Edit config.toml, then run
mssql-mcp-server --config config.toml
```

**Override specific settings:**
```bash
mssql-mcp-server --config config.toml --database AdventureWorks --query-timeout 120
```

**See [Configuration Guide](docs/CONFIGURATION.md) for complete documentation.**

### Configuration Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `server` | `localhost` | - | SQL Server hostname or IP |
| `database` | `master` | - | Target database name |
| `driver` | `ODBC Driver 17 for SQL Server` | - | ODBC driver name |
| `connection_timeout` | `30` | 1-300 | Connection timeout (seconds) |
| `query_timeout` | `30` | 1-3600 | Query execution timeout (seconds) |
| `max_retries` | `3` | 0-10 | Max retry attempts for transient errors |
| `retry_delay` | `1.0` | 0-60 | Base retry delay (seconds, exponential backoff) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SERVER` | `localhost` | SQL Server hostname or IP |
| `MSSQL_DATABASE` | `master` | Target database name |
| `ODBC_DRIVER` | `ODBC Driver 17 for SQL Server` | ODBC driver name |
| `MSSQL_CONNECTION_TIMEOUT` | `30` | Connection timeout (seconds) |
| `MSSQL_QUERY_TIMEOUT` | `30` | Query timeout (seconds) |
| `MSSQL_MAX_RETRIES` | `3` | Max retry attempts |
| `MSSQL_RETRY_DELAY` | `1.0` | Base retry delay (seconds) |

### Claude Code Configuration

#### Quick Install via CLI (Recommended)

The easiest way to add this MCP server to Claude Code:

```bash
claude mcp add mssql --transport stdio -e MSSQL_SERVER=your-server -e MSSQL_DATABASE=your-database -- pyodbc-mcp-server
```

**With all environment variables:**

```bash
claude mcp add mssql --transport stdio \
  -e MSSQL_SERVER=your-sql-server \
  -e MSSQL_DATABASE=your-database \
  -e ODBC_DRIVER="ODBC Driver 17 for SQL Server" \
  -- pyodbc-mcp-server
```

**Scope options:**

```bash
# User scope - available across all your projects (default)
claude mcp add mssql --transport stdio -e MSSQL_SERVER=your-server -e MSSQL_DATABASE=your-db -- pyodbc-mcp-server

# Project scope - shared with team via .mcp.json (checked into version control)
claude mcp add mssql --transport stdio --scope project -e MSSQL_SERVER=your-server -e MSSQL_DATABASE=your-db -- pyodbc-mcp-server
```

**Verify installation:**

```bash
claude mcp list          # List all configured servers
claude mcp get mssql     # Show details for this server
```

#### Manual Configuration (Alternative)

Add to your `~/.claude.json` (or `%USERPROFILE%\.claude.json` on Windows):

```json
{
  "mcpServers": {
    "mssql": {
      "type": "stdio",
      "command": "pyodbc-mcp-server",
      "env": {
        "MSSQL_SERVER": "your-sql-server",
        "MSSQL_DATABASE": "your-database"
      }
    }
  }
}
```

> **Note for Windows users:** If you encounter issues, try wrapping with `cmd /c`:
> ```json
> "command": "cmd",
> "args": ["/c", "pyodbc-mcp-server"],
> ```

### Claude Desktop Configuration

Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mssql": {
      "command": "python",
      "args": ["-m", "mssql_mcp_server"],
      "env": {
        "MSSQL_SERVER": "your-sql-server",
        "MSSQL_DATABASE": "your-database"
      }
    }
  }
}
```

## Usage Examples

Once configured, you can ask Claude to:

### Explore Schema
```
"List all tables in the dbo schema"
"Describe the structure of the customers table"
"What are the foreign key relationships for the orders table?"
```

### Query Data
```
"Show me the first 10 rows from the products table"
"Find all orders from the last 30 days"
"What are the top 5 customers by total order value?"
```

### Analyze Relationships
```
"Find all tables that reference the customer table"
"Show me the relationship between orders and order_lines"
```

## Security

This server is designed with security as a primary concern:

### Read-Only Enforcement

- Only queries starting with `SELECT` are allowed
- Dangerous keywords are blocked even in subqueries:
  - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`
  - `EXEC`, `EXECUTE`, `TRUNCATE`, `GRANT`, `REVOKE`, `DENY`
  - `BACKUP`, `RESTORE`, `SHUTDOWN`, `DBCC`

### Windows Authentication

- Uses `Trusted_Connection=yes` - no passwords stored or transmitted
- Leverages existing Windows domain security
- Your database permissions are enforced by SQL Server

### Row Limiting

- Default limit: 100 rows per query
- Maximum limit: 10,000 rows per query
- Prevents accidental retrieval of large datasets

### Error Handling & Retry Logic

- **Typed Exceptions**: ConnectionError, QueryError, SecurityError, ValidationError, TimeoutError
- **Automatic Retries**: Transient errors (connection failures, timeouts, deadlocks) are retried with exponential backoff
- **Configurable Timeouts**: Separate timeouts for connection and query execution
- **Consistent Error Format**: All errors returned as JSON with error code, message, and details

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Complete documentation for all 11 tools and 5 resources |
| [Configuration Guide](docs/CONFIGURATION.md) | CLI arguments, TOML files, environment variables |
| [Troubleshooting Guide](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Examples](docs/EXAMPLES.md) | Example queries and use cases |
| [Development Guide](docs/DEVELOPMENT.md) | Contributing, testing, and release process |

## Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/jjones-wps/pyodbc-mcp-server.git
cd pyodbc-mcp-server

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Check coverage
pytest --cov=src/mssql_mcp_server --cov-report=html

# Format code
black src tests && isort src tests

# Type check
mypy src

# Lint
ruff check src tests
```

### Running Locally

```bash
# Using environment variables
export MSSQL_SERVER=your-server
export MSSQL_DATABASE=your-database
python -m mssql_mcp_server

# Using config file
cp config.example.toml config.toml
# Edit config.toml
mssql-mcp-server --config config.toml

# Validate configuration
mssql-mcp-server --config config.toml --validate-only
```

**See [Development Guide](docs/DEVELOPMENT.md) for architecture, testing patterns, and contribution workflow.**

## Contributing

Contributions are welcome! Please see the [Development Guide](docs/DEVELOPMENT.md) for:

- Development setup
- Architecture overview
- Testing guide
- Code style requirements
- Adding new tools
- Release process

**Quick contribution checklist:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make changes and add tests
4. Ensure tests pass and coverage doesn't decrease
5. Format code (`black src tests && isort src tests`)
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) for MCP protocol handling
- Uses [pyodbc](https://github.com/mkleehammer/pyodbc) for SQL Server connectivity
- Inspired by the need for safe AI access to enterprise databases

## Related Projects

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Claude Code](https://claude.ai/code)
- [FastMCP](https://github.com/jlowin/fastmcp)
