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
- **Row limiting** - Prevents accidental large result sets (configurable, max 1000)
- **Schema exploration** - List tables, views, describe columns, find relationships
- **MCP compatible** - Works with Claude Code, Claude Desktop, and any MCP client

## Available Tools

| Tool | Description |
|------|-------------|
| `ListTables` | List all tables in the database, optionally filtered by schema |
| `ListViews` | List all views in the database, optionally filtered by schema |
| `DescribeTable` | Get column definitions for a specific table |
| `GetTableRelationships` | Find foreign key relationships for a table |
| `ReadData` | Execute a SELECT query (with security filtering) |

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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SERVER` | `localhost` | SQL Server hostname or IP |
| `MSSQL_DATABASE` | `master` | Target database name |
| `ODBC_DRIVER` | `ODBC Driver 17 for SQL Server` | ODBC driver name |

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
- Maximum limit: 1000 rows per query
- Prevents accidental retrieval of large datasets

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Running Locally

```bash
# Set environment variables
export MSSQL_SERVER=your-server
export MSSQL_DATABASE=your-database

# Run the server
python -m mssql_mcp_server
```

## Troubleshooting

### "ODBC Driver not found"

Install the Microsoft ODBC Driver for SQL Server:
- [Download ODBC Driver 17](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### "Login failed" or "Cannot connect"

1. Verify your Windows account has access to the SQL Server
2. Test connection with `sqlcmd -S your-server -d your-database -E`
3. Check firewall allows connection on port 1433

### "Tools not appearing in Claude Code"

1. Ensure `type: "stdio"` is in your config
2. Use the `cmd /c` wrapper on Windows
3. Restart Claude Code after config changes
4. Check Claude Code logs for MCP errors

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

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
