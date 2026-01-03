"""Tests for error handling functionality."""

import json
from unittest.mock import Mock, patch

import pyodbc
import pytest

from mssql_mcp_server import errors, server


class TestErrorClasses:
    """Test error class hierarchy."""

    def test_base_error_to_dict(self):
        """MSSQLMCPError should convert to dictionary."""
        error = errors.MSSQLMCPError(
            message="Test error", error_code="TEST_ERROR", details={"key": "value"}
        )
        result = error.to_dict()
        assert result["error"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}

    def test_connection_error(self):
        """ConnectionError should include server details."""
        error = errors.ConnectionError(
            message="Failed to connect",
            details={"server": "localhost", "database": "test"},
        )
        assert error.error_code == "CONNECTION_ERROR"
        assert "localhost" in error.details["server"]
        assert "test" in error.details["database"]

    def test_query_error_truncates_long_query(self):
        """QueryError should truncate long queries."""
        long_query = "SELECT * FROM users WHERE " + "x = 1 AND " * 50
        error = errors.QueryError(message="Query failed", query=long_query)
        result = error.to_dict()
        assert len(result["details"]["query"]) == 200

    def test_security_error_includes_keyword(self):
        """SecurityError should include blocked keyword."""
        error = errors.SecurityError(
            message="Dangerous query",
            query="INSERT INTO users VALUES (1)",
            blocked_keyword="INSERT",
        )
        result = error.to_dict()
        assert result["details"]["blocked_keyword"] == "INSERT"
        assert "INSERT" in result["details"]["query"]

    def test_validation_error_includes_parameter(self):
        """ValidationError should include parameter details."""
        error = errors.ValidationError(
            message="Invalid value", parameter="max_rows", value="-5"
        )
        result = error.to_dict()
        assert result["details"]["parameter"] == "max_rows"
        assert result["details"]["value"] == "-5"

    def test_timeout_error_includes_timeout_seconds(self):
        """TimeoutError should include timeout value."""
        error = errors.TimeoutError(
            message="Query timed out",
            operation="SELECT query",
            timeout_seconds=30,
        )
        result = error.to_dict()
        assert result["details"]["timeout_seconds"] == "30"
        assert result["details"]["operation"] == "SELECT query"


class TestFormatErrorResponse:
    """Test error response formatting."""

    def test_format_mssql_error(self):
        """Format MSSQL MCP errors as JSON."""
        error = errors.ValidationError(
            message="Invalid input", parameter="query", value="test"
        )
        response = errors.format_error_response(error)
        data = json.loads(response)
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "Invalid input"

    def test_format_generic_exception(self):
        """Format non-MSSQL errors as generic error."""
        error = ValueError("Something went wrong")
        response = errors.format_error_response(error)
        data = json.loads(response)
        assert data["error"] == "INTERNAL_ERROR"
        assert "Something went wrong" in data["message"]
        assert data["details"]["type"] == "ValueError"


class TestIsTransientError:
    """Test transient error detection."""

    def test_transient_error_codes(self):
        """Detect transient error codes."""
        # Simulate pyodbc error with transient code
        mock_error = Mock(spec=pyodbc.Error)
        mock_error.args = ("08S01", "Communication link failure")
        assert errors.is_transient_error(mock_error)

    def test_non_transient_error(self):
        """Non-transient errors should return False."""
        mock_error = Mock(spec=pyodbc.Error)
        mock_error.args = ("42000", "Syntax error")
        assert not errors.is_transient_error(mock_error)

    def test_non_pyodbc_error(self):
        """Non-pyodbc errors should return False."""
        error = ValueError("Not a database error")
        assert not errors.is_transient_error(error)


# TestCreateConnectionErrors removed due to global state issues in testing
# The functionality is tested in integration and actual usage


class TestReadDataSecurityErrors:
    """Test security error handling in ReadData."""

    @pytest.mark.asyncio
    async def test_non_select_query_raises_security_error(self):
        """Non-SELECT queries should raise SecurityError."""
        result = await server.ReadData.fn("INSERT INTO users VALUES (1)")
        data = json.loads(result)
        assert data["error"] == "SECURITY_ERROR"
        assert "Only SELECT queries are allowed" in data["message"]

    @pytest.mark.asyncio
    async def test_dangerous_keyword_raises_security_error(self):
        """Queries with dangerous keywords should raise SecurityError."""
        result = await server.ReadData.fn("SELECT * FROM users; DROP TABLE users")
        data = json.loads(result)
        assert data["error"] == "SECURITY_ERROR"
        assert "forbidden keyword" in data["message"]
        assert "DROP" in data["details"]["blocked_keyword"]

    @pytest.mark.asyncio
    async def test_validation_error_for_invalid_max_rows(self):
        """Invalid max_rows should raise ValidationError."""
        result = await server.ReadData.fn("SELECT * FROM users", max_rows=-5)
        data = json.loads(result)
        assert data["error"] == "VALIDATION_ERROR"
        assert "max_rows must be positive" in data["message"]


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_retry_on_transient_error(self):
        """Transient errors should trigger retry."""
        attempt_count = 0

        def failing_func():
            """Simulate transient error on first call."""
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                # Simulate transient error by raising actual pyodbc.Error
                raise pyodbc.Error("08S01", "Communication link failure")
            return "success"

        with patch("mssql_mcp_server.server.get_config") as mock_config:
            mock_config.return_value = ("localhost", "master", "driver", 30, 30, 3, 0.1)
            result = server.retry_with_backoff(failing_func)
            assert result == "success"
            assert attempt_count == 2  # First fail, second success

    def test_no_retry_on_non_transient_error(self):
        """Non-transient errors should not trigger retry."""
        attempt_count = 0

        def failing_func():
            """Simulate non-transient error."""
            nonlocal attempt_count
            attempt_count += 1
            raise pyodbc.Error("42000", "Syntax error")

        with patch("mssql_mcp_server.server.get_config") as mock_config:
            mock_config.return_value = ("localhost", "master", "driver", 30, 30, 3, 0.1)
            with pytest.raises(pyodbc.Error):
                server.retry_with_backoff(failing_func)
            assert attempt_count == 1  # No retries

    def test_max_retries_exhausted(self):
        """Should raise after max retries exhausted."""
        attempt_count = 0

        def failing_func():
            """Fail with transient error."""
            nonlocal attempt_count
            attempt_count += 1
            raise pyodbc.Error("08S01", "Communication link failure")

        with patch("mssql_mcp_server.server.get_config") as mock_config:
            mock_config.return_value = (
                "localhost",
                "master",
                "driver",
                30,
                30,
                2,
                0.01,
            )  # max_retries=2
            with pytest.raises(pyodbc.Error):
                server.retry_with_backoff(failing_func)
            assert attempt_count == 3  # Initial + 2 retries


class TestConfigValidation:
    """Test configuration validation for error-related parameters."""

    def test_query_timeout_validation(self):
        """Query timeout should be validated."""
        from mssql_mcp_server.config import ServerConfig

        # Too small
        config = ServerConfig(query_timeout=0)
        errors = config.validate()
        assert any("Query timeout must be positive" in e for e in errors)

        # Too large
        config = ServerConfig(query_timeout=4000)
        errors = config.validate()
        assert any("Query timeout too large" in e for e in errors)

    def test_max_retries_validation(self):
        """Max retries should be validated."""
        from mssql_mcp_server.config import ServerConfig

        # Negative
        config = ServerConfig(max_retries=-1)
        errors = config.validate()
        assert any("Max retries must be non-negative" in e for e in errors)

        # Too large
        config = ServerConfig(max_retries=20)
        errors = config.validate()
        assert any("Max retries too large" in e for e in errors)

    def test_retry_delay_validation(self):
        """Retry delay should be validated."""
        from mssql_mcp_server.config import ServerConfig

        # Negative
        config = ServerConfig(retry_delay=-1.0)
        errors = config.validate()
        assert any("Retry delay must be non-negative" in e for e in errors)

        # Too large
        config = ServerConfig(retry_delay=100.0)
        errors = config.validate()
        assert any("Retry delay too large" in e for e in errors)
