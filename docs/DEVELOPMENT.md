# Development Guide

Guide for contributors to MSSQL MCP Server.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Testing Guide](#testing-guide)
- [Code Style](#code-style)
- [Adding New Tools](#adding-new-tools)
- [Security Considerations](#security-considerations)
- [Release Process](#release-process)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- SQL Server (local or remote) for integration testing
- ODBC Driver 17 or 18 for SQL Server
- Git for version control

**Windows:**
```powershell
# Install Python
winget install Python.Python.3.12

# Install ODBC Driver
# Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

**Linux (Ubuntu/Debian):**
```bash
# Install Python
sudo apt install python3.12 python3.12-venv python3-pip

# Install ODBC Driver
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

---

## Development Setup

### Clone Repository

```bash
git clone https://github.com/yourusername/pyodbc-mcp-server.git
cd pyodbc-mcp-server
```

### Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate
```

### Install Development Dependencies

```bash
# Install package with development dependencies
pip install -e ".[dev]"

# This installs:
# - pytest (testing)
# - pytest-asyncio (async test support)
# - pytest-cov (coverage reporting)
# - black (code formatting)
# - isort (import sorting)
# - mypy (type checking)
# - ruff (linting)
# - build (package building)
```

### Verify Installation

```bash
# Run tests
pytest

# Check coverage
pytest --cov=src/mssql_mcp_server --cov-report=html

# Run type checking
mypy src

# Run linter
ruff check src tests
```

---

## Architecture Overview

### Project Structure

```
pyodbc-mcp-server/
├── src/
│   └── mssql_mcp_server/
│       ├── __init__.py          # Package exports
│       ├── __main__.py          # Entry point
│       ├── server.py            # Main server (11 tools, 5 resources)
│       ├── config.py            # Configuration management
│       ├── health.py            # Health checks
│       └── errors.py            # Error handling
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_server.py           # Server logic tests
│   ├── test_integration.py      # Integration tests
│   ├── test_resources.py        # Resource endpoint tests
│   ├── test_async.py            # Async behavior tests
│   ├── test_config.py           # Configuration tests
│   ├── test_health.py           # Health check tests
│   └── test_errors.py           # Error handling tests
├── docs/
│   ├── API.md                   # API documentation
│   ├── CONFIGURATION.md         # Configuration guide
│   ├── TROUBLESHOOTING.md       # Troubleshooting guide
│   ├── EXAMPLES.md              # Example queries
│   └── DEVELOPMENT.md           # This file
├── pyproject.toml               # Package configuration
├── config.example.toml          # Example configuration
├── ROADMAP.md                   # Development roadmap
├── CHANGELOG.md                 # Version history
└── README.md                    # Project overview
```

### Design Principles

**1. Read-Only by Design**
- All tools enforce read-only access through security filtering
- Two-layer security: prefix check (SELECT only) + keyword scanning (block INSERT, UPDATE, DELETE, etc.)
- Connection uses Windows Authentication (Trusted_Connection=yes)

**2. Per-Request Connections**
- Each MCP tool call creates a new database connection
- Connections are closed in `finally` block
- Stateless design (no connection pooling in current version)
- Future: Connection pooling via FastMCP lifespan API

**3. FastMCP Decorator Pattern**
- Tools registered via `@mcp.tool()` decorator
- Resources registered via `@mcp.resource(uri)` decorator
- Async tool functions with `async def`
- Error handling via `@handle_tool_errors` decorator

**4. Typed Error Handling**
- Custom exception hierarchy (MSSQLMCPError base class)
- Specific error types: ConnectionError, QueryError, SecurityError, ValidationError, TimeoutError
- Consistent JSON error response format
- Retry logic for transient errors with exponential backoff

---

## Testing Guide

### Test Structure

The test suite is organized by functionality:

| Test File | Purpose | Test Count |
|-----------|---------|------------|
| test_server.py | Core server logic, security filtering | 88 tests |
| test_integration.py | End-to-end tool testing | 14 tests |
| test_resources.py | MCP resource endpoints | 10 tests |
| test_async.py | Async behavior, thread safety | 11 tests |
| test_config.py | Configuration management | 31 tests |
| test_health.py | Health checks | 12 tests |
| test_errors.py | Error handling | 20 tests |
| **Total** | | **193 tests** |

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_server.py

# Run specific test class
pytest tests/test_server.py::TestSecurityFiltering

# Run specific test
pytest tests/test_server.py::TestSecurityFiltering::test_select_query_allowed

# Run with coverage
pytest --cov=src/mssql_mcp_server --cov-report=html

# Run with verbose output
pytest -v

# Run only failed tests from last run
pytest --lf

# Run tests matching pattern
pytest -k "security"
```

### Writing Tests

**Test Naming Convention:**
- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test methods: `test_<scenario>`

**Example Test:**
```python
import pytest
from mssql_mcp_server import server

class TestSecurityFiltering:
    """Test security filtering for read-only enforcement."""

    @pytest.mark.asyncio
    async def test_select_query_allowed(self):
        """SELECT queries should be allowed."""
        result = await server.ReadData.fn("SELECT * FROM Users", max_rows=10)
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_delete_query_blocked(self):
        """DELETE queries should be blocked with SecurityError."""
        result = await server.ReadData.fn("DELETE FROM Users WHERE UserId = 1")
        data = json.loads(result)
        assert data["error"] == "SECURITY_ERROR"
        assert "DELETE" in data["details"]["blocked_keyword"]
```

### Mock Fixtures

**conftest.py** provides shared fixtures:

```python
@pytest.fixture
def mock_connection():
    """Mock pyodbc connection."""
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    return conn

@pytest.fixture
def sample_tables():
    """Sample table data for testing."""
    return [
        ("dbo", "Users", "BASE TABLE"),
        ("dbo", "Orders", "BASE TABLE"),
        ("sales", "Customers", "BASE TABLE"),
    ]

# Use in tests:
def test_list_tables(mock_connection, sample_tables):
    mock_cursor = mock_connection.cursor()
    mock_cursor.fetchall.return_value = sample_tables
    # Test implementation
```

### Testing Patterns

**1. FastMCP Tool Testing:**

Tools are decorated with `@mcp.tool()`, access via `.fn()` attribute:

```python
# Correct:
result = await server.ListTables.fn()

# Incorrect (will fail):
result = await server.ListTables()
```

**2. Multi-Query Mocking:**

Use `side_effect` for tools that execute multiple queries:

```python
mock_cursor.fetchall.side_effect = [
    sample_tables,    # First query
    sample_columns,   # Second query
    sample_pks,       # Third query
    sample_fks        # Fourth query
]
```

**3. Column Name Case Sensitivity:**

Mock data column names must match query expectations:

```python
# Query uses: SELECT TABLE_SCHEMA, TABLE_NAME FROM ...
# Mock must return: ("TABLE_SCHEMA", "TABLE_NAME") not ("schema", "name")

# Correct:
sample_tables = [
    ("dbo", "Users", "BASE TABLE"),  # Matches query column order
]
```

### Coverage Requirements

- Minimum coverage: 15% (enforced in CI)
- Target coverage: 80%+
- Current coverage: 83.36%

**Check coverage:**
```bash
# Generate coverage report
pytest --cov=src/mssql_mcp_server --cov-report=html

# View HTML report
# Open htmlcov/index.html in browser
```

**Coverage thresholds in pyproject.toml:**
```toml
[tool.coverage.report]
fail_under = 15
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

## Code Style

### Formatting

**Black** (code formatter):
```bash
# Format all code
black src tests

# Check without modifying
black src tests --check

# Format specific file
black src/mssql_mcp_server/server.py
```

**isort** (import sorting):
```bash
# Sort imports
isort src tests

# Check without modifying
isort src tests --check-only
```

**Combined:**
```bash
# Format and sort imports
black src tests && isort src tests
```

### Type Checking

**mypy** (static type checking):
```bash
# Check all code
mypy src

# Check with strict mode
mypy src --strict

# Check specific file
mypy src/mssql_mcp_server/server.py
```

**Type Annotations:**
```python
# Good: Type annotations for function signatures
async def ListTables(schema_filter: str | None = None) -> str:
    """List all tables with optional schema filter."""
    pass

# Good: Type annotations for variables
connection: pyodbc.Connection = create_connection()
tables: list[dict[str, str]] = []

# Use modern union syntax (Python 3.10+)
def process(value: str | None) -> dict[str, str] | None:
    pass
```

### Linting

**ruff** (fast Python linter):
```bash
# Check all code
ruff check src tests

# Fix auto-fixable issues
ruff check src tests --fix

# Check specific rules
ruff check src --select E,F,W

# Ignore specific rules
ruff check src --ignore E501
```

### Docstrings

Follow **PEP 257** (imperative mood):

```python
def create_connection() -> pyodbc.Connection:
    """Create connection with error handling and query timeout.

    Returns:
        Active pyodbc connection

    Raises:
        ConnectionError: If connection fails

    """
    pass

class MSSQLMCPError(Exception):
    """Base exception for all MSSQL MCP Server errors.

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional context

    """
    pass
```

**PEP 257 Rules:**
- Use imperative mood ("Create connection" not "Creates connection")
- First line ends with period
- Summary line followed by blank line
- Multi-line docstrings have closing """ on separate line

---

## Adding New Tools

### Step-by-Step Guide

**1. Define Tool Function**

Add to `src/mssql_mcp_server/server.py`:

```python
@mcp.tool()
@handle_tool_errors
async def MyNewTool(parameter: str, optional_param: int = 100) -> str:
    """Tool description shown in MCP client.

    Args:
        parameter: Description of required parameter
        optional_param: Description of optional parameter (default: 100)

    Returns:
        JSON string with tool results

    """
    # Implementation
    conn = None
    try:
        conn = retry_with_backoff(create_connection)
        cursor = conn.cursor()

        # Execute query
        cursor.execute("SELECT ...")
        results = cursor.fetchall()

        # Format response
        return json.dumps({
            "result_count": len(results),
            "results": [{"key": "value"} for row in results]
        }, indent=2)

    finally:
        if conn:
            conn.close()
```

**2. Add Security Filtering (if needed)**

For query-based tools, add validation:

```python
# Validate input
if not parameter:
    raise ValidationError(
        message="Parameter cannot be empty",
        parameter="parameter",
        value=str(parameter)
    )

# Security check for query inputs
if any(keyword in parameter.upper() for keyword in DANGEROUS_KEYWORDS):
    raise SecurityError(
        message=f"Parameter contains forbidden content",
        query=parameter,
        blocked_keyword="DANGEROUS_CONTENT"
    )
```

**3. Write Tests**

Add to `tests/test_server.py`:

```python
class TestMyNewTool:
    """Test MyNewTool functionality."""

    @pytest.mark.asyncio
    async def test_basic_usage(self, mock_connection, mock_cursor):
        """MyNewTool should return expected results."""
        mock_cursor.fetchall.return_value = [("value1",), ("value2",)]

        with patch("mssql_mcp_server.server.create_connection", return_value=mock_connection):
            result = await server.MyNewTool.fn("test_param")

        data = json.loads(result)
        assert data["result_count"] == 2
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_validation_error(self):
        """Empty parameter should raise ValidationError."""
        result = await server.MyNewTool.fn("")
        data = json.loads(result)
        assert data["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_connection_closed(self, mock_connection):
        """Connection should be closed even on error."""
        with patch("mssql_mcp_server.server.create_connection", return_value=mock_connection):
            await server.MyNewTool.fn("test")

        mock_connection.close.assert_called()
```

**4. Update Documentation**

Add tool documentation to `docs/API.md`:

```markdown
### MyNewTool

Description of what the tool does.

**Parameters:**
- `parameter` (string, required): Description
- `optional_param` (number, optional): Description (default: 100)

**Returns:** JSON object with results

**Response Schema:**
\```json
{
  "result_count": "number",
  "results": [{"key": "value"}]
}
\```

**Example Usage:**
\```python
result = await MyNewTool("test_value", optional_param=200)
\```

**Example Response:**
\```json
{
  "result_count": 2,
  "results": [
    {"key": "value1"},
    {"key": "value2"}
  ]
}
\```
```

**5. Run Tests and Coverage**

```bash
# Run tests
pytest tests/test_server.py::TestMyNewTool -v

# Check coverage
pytest --cov=src/mssql_mcp_server --cov-report=term-missing

# Ensure coverage doesn't drop
```

**6. Update CHANGELOG.md**

Add entry under `[Unreleased]`:

```markdown
## [Unreleased]

### Added
- MyNewTool: Description of new functionality
```

---

## Security Considerations

### Read-Only Enforcement

**Two-Layer Security:**

1. **Query Prefix Check:**
   ```python
   query_upper = query.strip().upper()
   if not query_upper.startswith("SELECT"):
       raise SecurityError(...)
   ```

2. **Keyword Scanning:**
   ```python
   DANGEROUS_KEYWORDS = {
       "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
       "EXEC", "EXECUTE", "sp_executesql", "xp_cmdshell", ...
   }

   for keyword in DANGEROUS_KEYWORDS:
       # Use word boundary detection
       if f" {keyword} " in f" {query_upper} " or f" {keyword}(" in f" {query_upper} ":
           raise SecurityError(...)
   ```

**False Positive Prevention:**

Word boundary detection prevents false positives on column names:

```python
# Safe: Column named "updated_at"
"SELECT updated_at FROM Users"  # Not blocked

# Blocked: Actual UPDATE keyword
"UPDATE Users SET name = 'x'"   # Blocked
```

### Windows Authentication

**Never store credentials:**
- Use `Trusted_Connection=yes` (Windows Authentication)
- Credentials managed by Windows/Active Directory
- No passwords in configuration files
- Audit trail via Windows Security logs

### SQL Injection Prevention

**Parameterized queries** (when user input used in WHERE clause):

```python
# Bad: String concatenation (SQL injection risk)
cursor.execute(f"SELECT * FROM Users WHERE UserId = {user_id}")

# Good: Parameterized query
cursor.execute("SELECT * FROM Users WHERE UserId = ?", (user_id,))
```

**Note:** Current tools use fixed queries without user input in WHERE clauses, so parameterization not needed. If adding tools with dynamic WHERE clauses, use parameterized queries.

### Timeout Protection

Prevent resource exhaustion:

```python
# Set connection timeout
conn = pyodbc.connect(conn_str, timeout=connection_timeout)

# Set query timeout
conn.timeout = query_timeout
```

### Input Validation

Always validate user input:

```python
# Validate max_rows
if max_rows <= 0:
    raise ValidationError(
        message="max_rows must be positive",
        parameter="max_rows",
        value=str(max_rows)
    )

# Validate table_name format
if not table_name or ".." in table_name:
    raise ValidationError(
        message="Invalid table name",
        parameter="table_name",
        value=table_name
    )
```

---

## Release Process

### Version Numbering

Follow **Semantic Versioning** (SemVer):

- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

**1. Update Version**

```bash
# Update version in pyproject.toml
# version = "0.3.0"
```

**2. Update CHANGELOG.md**

```markdown
## [0.3.0] - 2026-01-03

### Added
- Comprehensive error handling with typed exceptions
- Retry logic for transient errors with exponential backoff
- Query timeout configuration

### Changed
- Updated configuration to include query_timeout, max_retries, retry_delay

### Fixed
- Connection cleanup on errors
```

**3. Run Full Test Suite**

```bash
# Run all tests
pytest

# Check coverage
pytest --cov=src/mssql_mcp_server --cov-report=html

# Run type checking
mypy src

# Run linter
ruff check src tests

# Format code
black src tests && isort src tests
```

**4. Build Package**

```bash
# Clean old builds
rm -rf dist/ build/

# Build package
python -m build

# Check package
twine check dist/*
```

**5. Create Git Tag**

```bash
# Commit changes
git add .
git commit -m "Release v0.3.0"

# Create tag
git tag -a v0.3.0 -m "Version 0.3.0 - Error handling and retry logic"

# Push tag
git push origin v0.3.0
git push origin main
```

**6. Publish to PyPI**

```bash
# Test PyPI (optional)
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*
```

**7. Create GitHub Release**

1. Go to https://github.com/yourusername/pyodbc-mcp-server/releases/new
2. Select tag `v0.3.0`
3. Title: `Version 0.3.0 - Error Handling and Retry Logic`
4. Description: Copy from CHANGELOG.md
5. Attach dist files (optional)
6. Publish release

---

## Contributing

### Contributing Workflow

**1. Fork and Clone**

```bash
# Fork on GitHub, then clone
git clone https://github.com/yourusername/pyodbc-mcp-server.git
cd pyodbc-mcp-server
```

**2. Create Branch**

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Or bug fix branch
git checkout -b fix/issue-123
```

**3. Make Changes**

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Make code changes
# Write tests
# Update documentation
```

**4. Run Tests**

```bash
# Run tests
pytest

# Check coverage
pytest --cov=src/mssql_mcp_server

# Format code
black src tests && isort src tests

# Type check
mypy src

# Lint
ruff check src tests
```

**5. Commit Changes**

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add MyNewTool for X functionality"

# Commit message format:
# feat: New feature
# fix: Bug fix
# docs: Documentation changes
# test: Test changes
# refactor: Code refactoring
# style: Code style changes
```

**6. Push and Create PR**

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create Pull Request on GitHub
# - Describe changes
# - Reference any issues
# - Include test results
```

### Code Review Process

**PR Requirements:**
1. All tests pass
2. Coverage doesn't decrease
3. Code formatted (black + isort)
4. Type checked (mypy)
5. Linted (ruff)
6. Documentation updated
7. CHANGELOG.md updated

**Review Checklist:**
- [ ] Code follows style guide
- [ ] Tests cover new functionality
- [ ] Documentation is clear
- [ ] No security issues
- [ ] Performance acceptable
- [ ] Backward compatible (or breaking change documented)

---

## Additional Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [pyodbc Documentation](https://github.com/mkleehammer/pyodbc/wiki)
- [SQL Server Documentation](https://docs.microsoft.com/en-us/sql/)
- [pytest Documentation](https://docs.pytest.org/)

---

## See Also

- [API Reference](API.md) - Complete tool documentation
- [Configuration Guide](CONFIGURATION.md) - Server configuration
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [Examples](EXAMPLES.md) - Example queries and use cases
