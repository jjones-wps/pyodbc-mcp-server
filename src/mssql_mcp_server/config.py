"""Configuration management for MSSQL MCP Server.

Supports multiple configuration sources with priority:
1. CLI arguments (highest priority)
2. Config file (TOML)
3. Environment variables
4. Defaults (lowest priority)
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("mssql_mcp_server.config")


class ServerConfig:
    """Server configuration with validation."""

    def __init__(
        self,
        server: str = "localhost",
        database: str = "master",
        driver: str = "ODBC Driver 17 for SQL Server",
        connection_timeout: int = 30,
        query_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        config_file: Path | None = None,
    ):
        """Initialize server configuration.

        Args:
            server: SQL Server hostname
            database: Database name
            driver: ODBC driver name
            connection_timeout: Connection timeout in seconds
            query_timeout: Query execution timeout in seconds
            max_retries: Maximum number of retry attempts for transient errors
            retry_delay: Base retry delay in seconds (exponential backoff)
            config_file: Path to TOML config file

        """
        self.server = server
        self.database = database
        self.driver = driver
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.config_file = config_file

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)

        """
        errors = []

        # Validate server
        if not self.server or not self.server.strip():
            errors.append("Server name cannot be empty")

        # Validate database
        if not self.database or not self.database.strip():
            errors.append("Database name cannot be empty")

        # Validate driver
        if not self.driver or not self.driver.strip():
            errors.append("ODBC driver name cannot be empty")

        # Validate connection timeout
        if self.connection_timeout <= 0:
            errors.append(
                f"Connection timeout must be positive (got {self.connection_timeout})"
            )
        elif self.connection_timeout > 300:
            errors.append(
                f"Connection timeout too large (got {self.connection_timeout}, max 300)"
            )

        # Validate query timeout
        if self.query_timeout <= 0:
            errors.append(f"Query timeout must be positive (got {self.query_timeout})")
        elif self.query_timeout > 3600:
            errors.append(
                f"Query timeout too large (got {self.query_timeout}, max 3600)"
            )

        # Validate max_retries
        if self.max_retries < 0:
            errors.append(f"Max retries must be non-negative (got {self.max_retries})")
        elif self.max_retries > 10:
            errors.append(f"Max retries too large (got {self.max_retries}, max 10)")

        # Validate retry_delay
        if self.retry_delay < 0:
            errors.append(f"Retry delay must be non-negative (got {self.retry_delay})")
        elif self.retry_delay > 60:
            errors.append(f"Retry delay too large (got {self.retry_delay}, max 60)")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as dictionary

        """
        return {
            "server": self.server,
            "database": self.database,
            "driver": self.driver,
            "connection_timeout": self.connection_timeout,
            "query_timeout": self.query_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
        }

    def __repr__(self) -> str:
        """Return string representation (safe, no secrets).

        Returns:
            String representation of configuration

        """
        return (
            f"ServerConfig(server={self.server!r}, "
            f"database={self.database!r}, "
            f"driver={self.driver!r}, "
            f"connection_timeout={self.connection_timeout}, "
            f"query_timeout={self.query_timeout}, "
            f"max_retries={self.max_retries}, "
            f"retry_delay={self.retry_delay})"
        )


def load_from_env() -> ServerConfig:
    """Load configuration from environment variables.

    Returns:
        Configuration loaded from environment

    """
    return ServerConfig(
        server=os.environ.get("MSSQL_SERVER", "localhost"),
        database=os.environ.get("MSSQL_DATABASE", "master"),
        driver=os.environ.get("ODBC_DRIVER", "ODBC Driver 17 for SQL Server"),
        connection_timeout=int(os.environ.get("MSSQL_CONNECTION_TIMEOUT", "30")),
        query_timeout=int(os.environ.get("MSSQL_QUERY_TIMEOUT", "30")),
        max_retries=int(os.environ.get("MSSQL_MAX_RETRIES", "3")),
        retry_delay=float(os.environ.get("MSSQL_RETRY_DELAY", "1.0")),
    )


def load_from_toml(config_path: Path) -> ServerConfig:
    """Load configuration from TOML file.

    Args:
        config_path: Path to TOML config file

    Returns:
        Configuration loaded from TOML

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If TOML is invalid or missing required fields

    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        import tomli
    except ImportError:
        # Try tomllib (Python 3.11+)
        try:
            import tomllib as tomli  # type: ignore
        except ImportError:
            raise ImportError(
                "TOML support requires 'tomli' package. Install with: pip install tomli"
            ) from None

    with config_path.open("rb") as f:
        data = tomli.load(f)

    # Look for [mssql] section
    if "mssql" not in data:
        raise ValueError(f"Config file missing [mssql] section: {config_path}")

    mssql_config = data["mssql"]

    return ServerConfig(
        server=mssql_config.get("server", "localhost"),
        database=mssql_config.get("database", "master"),
        driver=mssql_config.get("driver", "ODBC Driver 17 for SQL Server"),
        connection_timeout=mssql_config.get("connection_timeout", 30),
        query_timeout=mssql_config.get("query_timeout", 30),
        max_retries=mssql_config.get("max_retries", 3),
        retry_delay=mssql_config.get("retry_delay", 1.0),
        config_file=config_path,
    )


def parse_cli_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments (defaults to sys.argv)

    Returns:
        Parsed arguments namespace

    """
    parser = argparse.ArgumentParser(
        description="MSSQL MCP Server - Read-only SQL Server access via MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration Priority (highest to lowest):
  1. CLI arguments
  2. Config file (--config)
  3. Environment variables
  4. Defaults

Environment Variables:
  MSSQL_SERVER            SQL Server hostname (default: localhost)
  MSSQL_DATABASE          Database name (default: master)
  ODBC_DRIVER             ODBC driver name (default: ODBC Driver 17 for SQL Server)
  MSSQL_CONNECTION_TIMEOUT Connection timeout in seconds (default: 30)

Example:
  mssql-mcp-server --server sql.example.com --database MyDB
  mssql-mcp-server --config /path/to/config.toml
        """,
    )

    parser.add_argument(
        "--server",
        help="SQL Server hostname",
    )
    parser.add_argument(
        "--database",
        help="Database name",
    )
    parser.add_argument(
        "--driver",
        help="ODBC driver name",
    )
    parser.add_argument(
        "--connection-timeout",
        type=int,
        help="Connection timeout in seconds",
    )
    parser.add_argument(
        "--query-timeout",
        type=int,
        help="Query execution timeout in seconds",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum number of retry attempts for transient errors",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        help="Base retry delay in seconds (exponential backoff)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to TOML config file",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configuration and exit",
    )

    return parser.parse_args(args)


def load_config(args: list[str] | None = None) -> ServerConfig:
    """Load configuration from all sources with proper priority.

    Priority (highest to lowest):
    1. CLI arguments
    2. Config file
    3. Environment variables
    4. Defaults

    Args:
        args: Command-line arguments (defaults to sys.argv)

    Returns:
        Merged configuration

    Raises:
        SystemExit: If validation fails

    """
    cli_args = parse_cli_args(args)

    # Start with defaults/environment
    config = load_from_env()

    # Override with config file if specified
    if cli_args.config:
        try:
            file_config = load_from_toml(cli_args.config)
            # Merge file config (only non-default values)
            config.server = file_config.server
            config.database = file_config.database
            config.driver = file_config.driver
            config.connection_timeout = file_config.connection_timeout
            config.query_timeout = file_config.query_timeout
            config.max_retries = file_config.max_retries
            config.retry_delay = file_config.retry_delay
            config.config_file = file_config.config_file
            logger.info(f"Loaded configuration from {cli_args.config}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            raise SystemExit(1) from e

    # Override with CLI arguments (highest priority)
    if cli_args.server is not None:
        config.server = cli_args.server
    if cli_args.database is not None:
        config.database = cli_args.database
    if cli_args.driver is not None:
        config.driver = cli_args.driver
    if cli_args.connection_timeout is not None:
        config.connection_timeout = cli_args.connection_timeout
    if cli_args.query_timeout is not None:
        config.query_timeout = cli_args.query_timeout
    if cli_args.max_retries is not None:
        config.max_retries = cli_args.max_retries
    if cli_args.retry_delay is not None:
        config.retry_delay = cli_args.retry_delay

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise SystemExit(1)

    logger.info(
        f"Configuration loaded: server={config.server}, database={config.database}"
    )

    # If validate-only mode, exit after validation
    if cli_args.validate_only:
        print("✓ Configuration is valid")
        print(f"  Server: {config.server}")
        print(f"  Database: {config.database}")
        print(f"  Driver: {config.driver}")
        print(f"  Connection Timeout: {config.connection_timeout}s")
        raise SystemExit(0)

    return config
