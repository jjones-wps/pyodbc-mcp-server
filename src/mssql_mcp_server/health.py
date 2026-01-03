"""Health check functionality for MSSQL MCP Server."""

import logging

import pyodbc

from mssql_mcp_server.config import ServerConfig

logger = logging.getLogger("mssql_mcp_server.health")


class HealthCheckError(Exception):
    """Health check failed."""

    pass


def check_database_connection(config: ServerConfig) -> dict[str, str]:
    """Test database connection and retrieve basic information.

    Args:
        config: Server configuration

    Returns:
        Dictionary with connection info (version, database, server)

    Raises:
        HealthCheckError: If connection fails

    """
    conn_str = (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={config.server};"
        f"DATABASE={config.database};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str, timeout=config.connection_timeout)
        try:
            cursor = conn.cursor()

            # Get SQL Server version
            cursor.execute("SELECT @@VERSION AS version")
            version_row = cursor.fetchone()
            version = version_row.version if version_row else "Unknown"

            # Get database name (verify we're connected to the right database)
            cursor.execute("SELECT DB_NAME() AS database_name")
            db_row = cursor.fetchone()
            database_name = db_row.database_name if db_row else "Unknown"

            # Get server name
            cursor.execute("SELECT @@SERVERNAME AS server_name")
            server_row = cursor.fetchone()
            server_name = server_row.server_name if server_row else "Unknown"

            return {
                "status": "healthy",
                "version": version.split("\n")[0][:100],  # First line, truncated
                "database": database_name,
                "server": server_name,
            }
        finally:
            conn.close()

    except pyodbc.Error as e:
        error_msg = str(e)
        logger.error(f"Database connection failed: {error_msg}")

        # Provide helpful error messages
        if "Login timeout expired" in error_msg:
            raise HealthCheckError(
                f"Connection timeout to {config.server}. "
                "Check server name and network connectivity."
            ) from e
        elif "Cannot open database" in error_msg:
            raise HealthCheckError(
                f"Cannot open database '{config.database}' on {config.server}. "
                "Check database name and permissions."
            ) from e
        elif "Login failed" in error_msg:
            raise HealthCheckError(
                f"Login failed for {config.server}. "
                "Check Windows Authentication permissions."
            ) from e
        elif "Data source name not found" in error_msg or "driver" in error_msg.lower():
            raise HealthCheckError(
                f"ODBC driver '{config.driver}' not found. "
                "Install ODBC Driver 17 or 18 for SQL Server."
            ) from e
        else:
            raise HealthCheckError(f"Database connection failed: {error_msg}") from e


def run_health_check(config: ServerConfig, verbose: bool = True) -> bool:
    """Run health check and log results.

    Args:
        config: Server configuration
        verbose: Whether to print detailed results

    Returns:
        True if healthy, False otherwise

    """
    try:
        result = check_database_connection(config)

        if verbose:
            logger.info("✓ Database connection successful")
            logger.info(f"  Server: {result['server']}")
            logger.info(f"  Database: {result['database']}")
            logger.info(f"  Version: {result['version']}")

        return True

    except HealthCheckError as e:
        if verbose:
            logger.error(f"✗ Health check failed: {e}")
        return False
