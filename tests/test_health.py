"""Tests for health check module."""

from unittest.mock import MagicMock, patch

import pyodbc
import pytest

from mssql_mcp_server.config import ServerConfig
from mssql_mcp_server.health import (
    HealthCheckError,
    check_database_connection,
    run_health_check,
)


class MockRow:
    """Mock database row object."""

    def __init__(self, **kwargs):
        """Initialize mock row with attributes."""
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_config():
    """Return standard test configuration."""
    return ServerConfig(
        server="test-server",
        database="test-db",
        driver="ODBC Driver 17 for SQL Server",
        connection_timeout=30,
    )


@pytest.fixture
def mock_cursor():
    """Mock database cursor."""
    cursor = MagicMock()
    cursor.fetchone = MagicMock()
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    conn.close = MagicMock()
    return conn


class TestCheckDatabaseConnection:
    """Tests for check_database_connection function."""

    def test_successful_connection(self, mock_config, mock_connection, mock_cursor):
        """Successful connection should return database info."""
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            MockRow(version="Microsoft SQL Server 2019 (RTM) - 15.0.2000.5"),
            MockRow(database_name="test-db"),
            MockRow(server_name="TEST-SERVER"),
        ]

        with patch(
            "mssql_mcp_server.health.pyodbc.connect", return_value=mock_connection
        ):
            result = check_database_connection(mock_config)

            assert result["status"] == "healthy"
            assert "Microsoft SQL Server 2019" in result["version"]
            assert result["database"] == "test-db"
            assert result["server"] == "TEST-SERVER"

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    def test_connection_timeout(self, mock_config):
        """Connection timeout should raise HealthCheckError with helpful message."""
        error = pyodbc.Error("08001", "[08001] Login timeout expired")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with pytest.raises(HealthCheckError, match="Connection timeout"):
                check_database_connection(mock_config)

    def test_database_not_found(self, mock_config):
        """Database not found should raise HealthCheckError with helpful message."""
        error = pyodbc.Error("42000", "[42000] Cannot open database 'test-db'")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with pytest.raises(HealthCheckError, match="Cannot open database"):
                check_database_connection(mock_config)

    def test_login_failed(self, mock_config):
        """Login failure should raise HealthCheckError with helpful message."""
        error = pyodbc.Error("28000", "[28000] Login failed for user")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with pytest.raises(HealthCheckError, match="Login failed"):
                check_database_connection(mock_config)

    def test_driver_not_found(self, mock_config):
        """Driver not found should raise HealthCheckError with helpful message."""
        error = pyodbc.Error("IM002", "[IM002] Data source name not found")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with pytest.raises(HealthCheckError, match="ODBC driver.*not found"):
                check_database_connection(mock_config)

    def test_generic_error(self, mock_config):
        """Generic errors should raise HealthCheckError with error message."""
        error = pyodbc.Error("HY000", "[HY000] Unknown error occurred")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with pytest.raises(HealthCheckError, match="Database connection failed"):
                check_database_connection(mock_config)

    def test_connection_closed_on_error(
        self, mock_config, mock_connection, mock_cursor
    ):
        """Connection should be closed even if query fails."""
        # Connection succeeds but query fails
        mock_cursor.execute.side_effect = Exception("Query failed")

        with patch(
            "mssql_mcp_server.health.pyodbc.connect", return_value=mock_connection
        ):
            with pytest.raises(Exception, match="Query failed"):
                check_database_connection(mock_config)

        # Verify connection was still closed
        mock_connection.close.assert_called_once()

    def test_version_truncation(self, mock_config, mock_connection, mock_cursor):
        """Long version strings should be truncated to 100 chars (first line only)."""
        long_version = (
            "Microsoft SQL Server 2019 (RTM-CU8) (KB4577194) - 15.0.4073.23 (X64)\n"
            "Sep 23 2020 16:03:08\n"
            "Copyright (C) 2019 Microsoft Corporation\n"
            "Enterprise Edition (64-bit) on Windows Server 2019 Standard 10.0 <X64> (Build 17763: ) (Hypervisor)\n"
        )

        mock_cursor.fetchone.side_effect = [
            MockRow(version=long_version),
            MockRow(database_name="test-db"),
            MockRow(server_name="TEST-SERVER"),
        ]

        with patch(
            "mssql_mcp_server.health.pyodbc.connect", return_value=mock_connection
        ):
            result = check_database_connection(mock_config)

            # Should only include first line, truncated to 100 chars
            assert len(result["version"]) <= 100
            assert "\n" not in result["version"]
            assert "Microsoft SQL Server 2019" in result["version"]


class TestRunHealthCheck:
    """Tests for run_health_check function."""

    def test_successful_health_check_verbose(
        self, mock_config, mock_connection, mock_cursor
    ):
        """Successful health check with verbose=True should log results."""
        mock_cursor.fetchone.side_effect = [
            MockRow(version="Microsoft SQL Server 2019"),
            MockRow(database_name="test-db"),
            MockRow(server_name="TEST-SERVER"),
        ]

        with patch(
            "mssql_mcp_server.health.pyodbc.connect", return_value=mock_connection
        ):
            with patch("mssql_mcp_server.health.logger") as mock_logger:
                result = run_health_check(mock_config, verbose=True)

                assert result is True
                # Verify logging occurred
                assert mock_logger.info.call_count >= 1

    def test_successful_health_check_quiet(
        self, mock_config, mock_connection, mock_cursor
    ):
        """Successful health check with verbose=False should not log details."""
        mock_cursor.fetchone.side_effect = [
            MockRow(version="Microsoft SQL Server 2019"),
            MockRow(database_name="test-db"),
            MockRow(server_name="TEST-SERVER"),
        ]

        with patch(
            "mssql_mcp_server.health.pyodbc.connect", return_value=mock_connection
        ):
            result = run_health_check(mock_config, verbose=False)

            assert result is True

    def test_failed_health_check_verbose(self, mock_config):
        """Failed health check with verbose=True should log error."""
        error = pyodbc.Error("08001", "[08001] Login timeout expired")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            with patch("mssql_mcp_server.health.logger") as mock_logger:
                result = run_health_check(mock_config, verbose=True)

                assert result is False
                # Verify error logging occurred
                assert mock_logger.error.call_count >= 1

    def test_failed_health_check_quiet(self, mock_config):
        """Failed health check with verbose=False should not log."""
        error = pyodbc.Error("08001", "[08001] Login timeout expired")

        with patch("mssql_mcp_server.health.pyodbc.connect", side_effect=error):
            result = run_health_check(mock_config, verbose=False)

            assert result is False
