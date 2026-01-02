# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSSQL MCP Server - A Model Context Protocol server providing read-only SQL Server access via Windows Authentication. Uses FastMCP for protocol handling and pyodbc for database connectivity.

## Development Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests with coverage
pytest

# Run a single test file
pytest tests/test_server.py

# Run a specific test
pytest tests/test_server.py::TestSecurityFiltering::test_select_query_allowed

# Run the server locally (requires env vars)
python -m mssql_mcp_server

# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SERVER` | `localhost` | SQL Server hostname |
| `MSSQL_DATABASE` | `master` | Target database |
| `ODBC_DRIVER` | `ODBC Driver 17 for SQL Server` | ODBC driver name |

**⚠️ SECURITY WARNING**: Never store sensitive credentials in `.env` files within the repository directory. Use `.env.example` as a template and create your local `.env` file outside the repository, or use GitHub Secrets for CI/CD tokens.

## Architecture

### Single-File Server Design

The entire MCP server lives in `src/mssql_mcp_server/server.py`. This file contains:
- Database connection logic using pyodbc with `Trusted_Connection=yes`
- All five MCP tools decorated with `@mcp.tool()`
- Security filtering logic for read-only enforcement

### MCP Tool Structure

Tools are registered via FastMCP decorator pattern:
```python
mcp = FastMCP("mssql-readonly")

@mcp.tool()
def ToolName(args) -> str:
    # Returns JSON string
```

### Security Model

The `ReadData` tool implements security at two levels:

1. **Query prefix check**: Only queries starting with `SELECT` are allowed
2. **Keyword scanning**: Blocks dangerous keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `EXEC`, etc.) even in subqueries

The keyword check uses word boundary detection to avoid false positives on column names like `updated_at`.

### Connection Pattern

Each tool call creates a new connection and closes it in a `finally` block. This stateless design ensures:
- No connection pooling complexity
- Clean resource management
- Windows Authentication credentials used fresh each call

## Testing Approach

Tests in `tests/test_server.py` are **logic-only unit tests** that don't require a database connection. They test:
- Security filtering rules
- Row limiting behavior
- Table name parsing (schema.table format)

To add integration tests requiring a database, you would need to mock `pyodbc.connect` or set up a test SQL Server instance.

## Package Entry Points

- **Module execution**: `python -m mssql_mcp_server` triggers `__main__.py`
- **Script entry**: `pyodbc-mcp-server` command (defined in pyproject.toml)
- Both call `server.main()` which runs `mcp.run()`

---

## Project Health & Quality Standards

**Status**: 🟢 **Excellent** (88/100) - Comprehensive audit completed 2026-01-02

### Recent Quality Improvements

All critical, high, and medium-priority issues from the comprehensive project audit have been resolved:

- ✅ **Security**: API token exposure mitigated, .env.example template created
- ✅ **Development Environment**: Virtual environment setup, all dev dependencies installed
- ✅ **Cache Cleanup**: Removed .mypy_cache, .ruff_cache, .coverage files
- ✅ **Dependencies**: Removed redundant requirements.txt (pyproject.toml is single source of truth)
- ✅ **Coverage**: 15% minimum threshold enforced in CI and locally
- ✅ **PEP 257**: All 27 docstring compliance issues resolved
- ✅ **CI/CD**: Codecov now fails CI on error, coverage thresholds enforced

### Quality Metrics

| Metric | Status | Details |
|--------|--------|---------|
| Test Coverage | 16.98% | Above 15% threshold, HTML reports enabled |
| PEP 257 Compliance | ✅ | All docstrings follow imperative mood |
| Code Quality | ✅ | Ruff + mypy + pre-commit hooks |
| CI/CD | ✅ | GitHub Actions with Windows testing |
| Documentation | ✅ | Comprehensive docs across 6 files |

### Development Standards Enforced

- **Testing**: pytest with coverage threshold (15% minimum)
- **Linting**: ruff with PEP 257 docstring checks
- **Type Checking**: mypy with strict imports
- **Pre-commit**: 8 hooks including security checks
- **CI**: Automated lint, test (3.10/3.11/3.12), and build

---

## Development Roadmap

This project is actively being improved. See the planning documents for details:

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Phased feature roadmap with milestones |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Current vs target architecture diagrams |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Detailed technical specifications |
| [docs/ISSUES.md](docs/ISSUES.md) | GitHub issue templates |

### Current Phase: Foundation (v0.2.0)

Active work focuses on:
1. **Async conversion** - Wrap pyodbc calls with `asyncer.asyncify()`
2. **Connection pooling** - Implement via FastMCP lifespan API
3. **MCP Resources** - Add `@mcp.resource()` for tables
4. **Context logging** - Use `ctx.info()`, `ctx.debug()`, etc.

### Key Architectural Changes Planned

```
Current (v0.1.0)          Target (v1.0.0)
─────────────────         ─────────────────
Sync tools         →      Async tools
New conn per call  →      Connection pool
Tools only         →      Tools + Resources
No logging         →      Context-based logging
Basic tests        →      Integration tests
```

### Adding New Features

When implementing roadmap items:

1. Check `docs/IMPLEMENTATION_PLAN.md` for specifications
2. Follow the async pattern with Context injection:
   ```python
   @mcp.tool()
   async def NewTool(arg: str, ctx: Context = None) -> str:
       pool = ctx.request_context.lifespan_context["pool"]
       await ctx.info(f"NewTool called with {arg}")
       # ... implementation
   ```
3. Add tests in `tests/` with mock fixtures
4. Update CHANGELOG.md

### Dependencies to Add

Phase 1 requires these new dependencies (not yet in pyproject.toml):
- `asyncer>=0.0.2` - Async wrapper for sync code
- `pytest-asyncio>=0.21.0` - Async test support
