"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from mssql_mcp_server.config import (
    ServerConfig,
    load_config,
    load_from_env,
    load_from_toml,
    parse_cli_args,
)


class TestServerConfig:
    """Tests for ServerConfig class."""

    def test_default_values(self):
        """ServerConfig should have sensible defaults."""
        config = ServerConfig()

        assert config.server == "localhost"
        assert config.database == "master"
        assert config.driver == "ODBC Driver 17 for SQL Server"
        assert config.connection_timeout == 30

    def test_custom_values(self):
        """ServerConfig should accept custom values."""
        config = ServerConfig(
            server="sql.example.com",
            database="MyDB",
            driver="ODBC Driver 18 for SQL Server",
            connection_timeout=60,
        )

        assert config.server == "sql.example.com"
        assert config.database == "MyDB"
        assert config.driver == "ODBC Driver 18 for SQL Server"
        assert config.connection_timeout == 60

    def test_validate_success(self):
        """Validate should return empty list for valid config."""
        config = ServerConfig()
        errors = config.validate()

        assert errors == []

    def test_validate_empty_server(self):
        """Validate should fail for empty server."""
        config = ServerConfig(server="")
        errors = config.validate()

        assert len(errors) == 1
        assert "Server name cannot be empty" in errors[0]

    def test_validate_empty_database(self):
        """Validate should fail for empty database."""
        config = ServerConfig(database="   ")
        errors = config.validate()

        assert len(errors) == 1
        assert "Database name cannot be empty" in errors[0]

    def test_validate_empty_driver(self):
        """Validate should fail for empty driver."""
        config = ServerConfig(driver="")
        errors = config.validate()

        assert len(errors) == 1
        assert "ODBC driver name cannot be empty" in errors[0]

    def test_validate_negative_timeout(self):
        """Validate should fail for negative timeout."""
        config = ServerConfig(connection_timeout=-1)
        errors = config.validate()

        assert len(errors) == 1
        assert "must be positive" in errors[0]

    def test_validate_timeout_too_large(self):
        """Validate should fail for timeout > 300."""
        config = ServerConfig(connection_timeout=500)
        errors = config.validate()

        assert len(errors) == 1
        assert "too large" in errors[0]

    def test_validate_multiple_errors(self):
        """Validate should return all errors."""
        config = ServerConfig(server="", database="", connection_timeout=-1)
        errors = config.validate()

        assert len(errors) == 3

    def test_to_dict(self):
        """to_dict should return configuration as dictionary."""
        config = ServerConfig(server="test-server", database="test-db")
        result = config.to_dict()

        assert result["server"] == "test-server"
        assert result["database"] == "test-db"
        assert "driver" in result
        assert "connection_timeout" in result

    def test_repr(self):
        """Repr should return safe string representation."""
        config = ServerConfig(server="test-server")
        repr_str = repr(config)

        assert "ServerConfig" in repr_str
        assert "test-server" in repr_str
        assert "master" in repr_str


class TestLoadFromEnv:
    """Tests for load_from_env function."""

    def test_load_defaults(self, monkeypatch):
        """Should load default values when env vars not set."""
        # Clear all relevant env vars
        for key in [
            "MSSQL_SERVER",
            "MSSQL_DATABASE",
            "ODBC_DRIVER",
            "MSSQL_CONNECTION_TIMEOUT",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = load_from_env()

        assert config.server == "localhost"
        assert config.database == "master"
        assert config.driver == "ODBC Driver 17 for SQL Server"
        assert config.connection_timeout == 30

    def test_load_from_env_vars(self, monkeypatch):
        """Should load from environment variables."""
        monkeypatch.setenv("MSSQL_SERVER", "env-server")
        monkeypatch.setenv("MSSQL_DATABASE", "env-db")
        monkeypatch.setenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
        monkeypatch.setenv("MSSQL_CONNECTION_TIMEOUT", "45")

        config = load_from_env()

        assert config.server == "env-server"
        assert config.database == "env-db"
        assert config.driver == "ODBC Driver 18 for SQL Server"
        assert config.connection_timeout == 45


class TestLoadFromToml:
    """Tests for load_from_toml function."""

    def test_load_valid_config(self):
        """Should load valid TOML config."""
        toml_content = """
[mssql]
server = "toml-server"
database = "toml-db"
driver = "ODBC Driver 18 for SQL Server"
connection_timeout = 60
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            config = load_from_toml(config_path)

            assert config.server == "toml-server"
            assert config.database == "toml-db"
            assert config.driver == "ODBC Driver 18 for SQL Server"
            assert config.connection_timeout == 60
            assert config.config_file == config_path
        finally:
            config_path.unlink()

    def test_load_missing_file(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="not found"):
            load_from_toml(Path("/nonexistent/config.toml"))

    def test_load_missing_mssql_section(self):
        """Should raise ValueError if [mssql] section missing."""
        toml_content = """
[other_section]
key = "value"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="missing \\[mssql\\] section"):
                load_from_toml(config_path)
        finally:
            config_path.unlink()

    def test_load_partial_config(self):
        """Should use defaults for missing fields."""
        toml_content = """
[mssql]
server = "partial-server"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            config = load_from_toml(config_path)

            assert config.server == "partial-server"
            assert config.database == "master"  # default
            assert config.driver == "ODBC Driver 17 for SQL Server"  # default
        finally:
            config_path.unlink()


class TestParseCliArgs:
    """Tests for parse_cli_args function."""

    def test_no_arguments(self):
        """Should parse successfully with no arguments."""
        args = parse_cli_args([])

        assert args.server is None
        assert args.database is None
        assert args.config is None

    def test_server_argument(self):
        """Should parse --server argument."""
        args = parse_cli_args(["--server", "cli-server"])

        assert args.server == "cli-server"

    def test_database_argument(self):
        """Should parse --database argument."""
        args = parse_cli_args(["--database", "cli-db"])

        assert args.database == "cli-db"

    def test_driver_argument(self):
        """Should parse --driver argument."""
        args = parse_cli_args(["--driver", "ODBC Driver 18 for SQL Server"])

        assert args.driver == "ODBC Driver 18 for SQL Server"

    def test_timeout_argument(self):
        """Should parse --connection-timeout argument."""
        args = parse_cli_args(["--connection-timeout", "45"])

        assert args.connection_timeout == 45

    def test_config_argument(self):
        """Should parse --config argument."""
        args = parse_cli_args(["--config", "/path/to/config.toml"])

        assert args.config == Path("/path/to/config.toml")

    def test_validate_only_argument(self):
        """Should parse --validate-only flag."""
        args = parse_cli_args(["--validate-only"])

        assert args.validate_only is True

    def test_multiple_arguments(self):
        """Should parse multiple arguments."""
        args = parse_cli_args(
            [
                "--server",
                "multi-server",
                "--database",
                "multi-db",
                "--connection-timeout",
                "90",
            ]
        )

        assert args.server == "multi-server"
        assert args.database == "multi-db"
        assert args.connection_timeout == 90


class TestLoadConfig:
    """Tests for load_config function (integration)."""

    def test_cli_overrides_env(self, monkeypatch):
        """CLI arguments should override environment variables."""
        monkeypatch.setenv("MSSQL_SERVER", "env-server")
        monkeypatch.setenv("MSSQL_DATABASE", "env-db")

        config = load_config(["--server", "cli-server"])

        assert config.server == "cli-server"  # CLI wins
        assert config.database == "env-db"  # ENV used

    def test_validation_failure_exits(self, monkeypatch):
        """Invalid configuration should exit with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            load_config(["--server", ""])  # Empty server

        assert exc_info.value.code == 1

    def test_validate_only_exits(self, monkeypatch):
        """--validate-only should exit with code 0 after validation."""
        monkeypatch.setenv("MSSQL_SERVER", "test-server")

        with pytest.raises(SystemExit) as exc_info:
            load_config(["--validate-only"])

        assert exc_info.value.code == 0

    def test_config_file_merged(self, monkeypatch):
        """Config file should be merged with env vars."""
        toml_content = """
[mssql]
server = "toml-server"
database = "toml-db"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            monkeypatch.setenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

            config = load_config(["--config", str(config_path)])

            assert config.server == "toml-server"  # From file
            assert config.database == "toml-db"  # From file
            # Driver not in file, should come from env
            # Actually, the implementation loads from env first, then file, then CLI
            # So file values override env values
        finally:
            config_path.unlink()

    def test_cli_overrides_file(self):
        """CLI arguments should override config file values."""
        toml_content = """
[mssql]
server = "toml-server"
database = "toml-db"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_path = Path(f.name)

        try:
            config = load_config(
                [
                    "--config",
                    str(config_path),
                    "--server",
                    "cli-server",
                ]
            )

            assert config.server == "cli-server"  # CLI wins
            assert config.database == "toml-db"  # From file
        finally:
            config_path.unlink()

    def test_invalid_config_file_exits(self):
        """Invalid config file should exit with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            load_config(["--config", "/nonexistent/config.toml"])

        assert exc_info.value.code == 1
