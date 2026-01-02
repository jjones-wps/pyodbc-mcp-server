# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2026-01-02

### Added
- Pytest coverage thresholds (minimum 15% required)
- HTML coverage reports for detailed analysis
- Coverage.py configuration with proper source paths and omit patterns
- PEP 257 docstring compliance enforcement via ruff
- Security documentation templates (.env.example)

### Changed
- CI workflow now enforces coverage thresholds (--cov-fail-under=15)
- Codecov upload now fails CI on error (fail_ci_if_error: true)
- All module and tool docstrings updated to PEP 257 standards
- Tool docstrings converted to imperative mood (List vs Lists)
- Development environment setup documented and verified

### Fixed
- All 27 PEP 257 docstring compliance issues resolved
- Module docstring formatting (added period to first line)
- Docstring whitespace and blank line formatting

### Removed
- Redundant requirements.txt file (pyproject.toml is single source of truth)
- Cache directory pollution (.mypy_cache, .ruff_cache, .coverage)

## [0.2.2] - 2025-12-12

### Added
- Claude Code CLI installation instructions using `claude mcp add` (recommended method)
- Scope options documentation (user vs project scope)
- Server management commands (`claude mcp list`, `claude mcp get`)

### Changed
- Simplified manual configuration examples in README

## [0.2.1] - 2024-12-11

### Changed
- Renamed package from `mssql-mcp-server` to `pyodbc-mcp-server` for PyPI availability
- Updated all repository URLs and references

### Fixed
- Documentation updates for public release
- Fixed clone URLs and installation paths in README

## [0.2.0] - 2024-12-11

### Added
- **Async Architecture**: All tools now use `async`/`await` with `anyio.to_thread` for non-blocking database operations
- **Per-Request Connections**: Thread-safe connection pattern - fresh connections created per-request within worker threads (ODBC driver handles pooling at driver level)
- **MCP Resources**: 5 new resources for schema discovery:
  - `mssql://tables` - List all tables in the database
  - `mssql://views` - List all views in the database
  - `mssql://schema/{schema_name}` - Tables filtered by schema
  - `mssql://table/{table_name}/preview` - Preview table data (first 10 rows)
  - `mssql://info` - Database server information
- **Structured Logging**: Python `logging` module integration for operation tracking

### Changed
- Upgraded `fastmcp` dependency from `>=0.1.0` to `>=2.0.0`
- Added `anyio>=4.0.0` dependency for async thread pooling
- Added `pytest-asyncio>=0.23.0` to dev dependencies
- Tools now run database calls in background threads to prevent blocking
- Improved type annotations (using `X | None` instead of `Optional[X]`)

### Fixed
- Thread safety ensured via per-request connection pattern (pyodbc threadsafety=1 compliance)

## [0.1.0] - 2024-12-10

### Added
- Initial release
- `ListTables` tool - List all tables in the database
- `ListViews` tool - List all views in the database
- `DescribeTable` tool - Get column definitions for a table
- `GetTableRelationships` tool - Find foreign key relationships
- `ReadData` tool - Execute SELECT queries with security filtering
- Windows Authentication support via pyodbc Trusted_Connection
- Read-only enforcement with dangerous keyword blocking
- Row limiting (max 1000 rows per query)
- Claude Code and Claude Desktop configuration examples
