# Contributing to MSSQL MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Windows (required for pyodbc with Windows Authentication)
- ODBC Driver 17+ for SQL Server
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jjones-wps/pyodbc-mcp-server.git
   cd pyodbc-mcp-server
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Workflow

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Checking

```bash
mypy src/ --ignore-missing-imports
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_server.py

# Run specific test
pytest tests/test_server.py::TestSecurityFiltering::test_select_query_allowed
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

## Making Changes

### Branch Naming

- `feature/` - New features (e.g., `feature/list-indexes-tool`)
- `fix/` - Bug fixes (e.g., `fix/connection-timeout`)
- `docs/` - Documentation changes
- `refactor/` - Code refactoring

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(tools): add ListIndexes tool for index discovery

fix(security): block EXEC keyword in subqueries

docs(readme): add Claude Desktop configuration example
```

## Pull Request Process

1. **Create a feature branch** from `master`
2. **Make your changes** with appropriate tests
3. **Ensure all checks pass**:
   - `ruff check src/ tests/`
   - `ruff format --check src/ tests/`
   - `pytest`
4. **Update documentation** if needed
5. **Update CHANGELOG.md** under `[Unreleased]`
6. **Submit a pull request**

### PR Requirements

- Clear description of changes
- Tests for new functionality
- Documentation updates (if applicable)
- All CI checks passing

## Project Structure

```
pyodbc-mcp-server/
├── src/mssql_mcp_server/    # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   └── server.py            # MCP server implementation
├── tests/                   # Test files
├── docs/                    # Documentation
├── .github/                 # GitHub configuration
│   ├── workflows/           # CI/CD workflows
│   └── ISSUE_TEMPLATE/      # Issue templates
├── pyproject.toml           # Project configuration
├── CHANGELOG.md             # Version history
├── ROADMAP.md               # Development roadmap
└── SECURITY.md              # Security policy
```

## Reporting Issues

- **Bugs**: Use the bug report template
- **Features**: Use the feature request template
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

## Questions?

Open a GitHub Discussion or issue for questions about contributing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
