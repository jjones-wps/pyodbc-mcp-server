"""Error handling for MSSQL MCP Server.

Defines typed exceptions for different error scenarios to provide
clear, actionable error messages to MCP clients.
"""


class MSSQLMCPError(Exception):
    """Base exception for all MSSQL MCP Server errors.

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional context

    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, str] | None = None,
    ):
        """Initialize MSSQL MCP error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context

        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, str | dict[str, str]]:
        """Convert error to dictionary for JSON serialization.

        Returns:
            Error data as dictionary

        """
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ConnectionError(MSSQLMCPError):
    """Database connection failed.

    Raised when unable to establish connection to SQL Server.
    Common causes: server unreachable, timeout, authentication failure.
    """

    def __init__(self, message: str, details: dict[str, str] | None = None):
        """Initialize connection error.

        Args:
            message: Human-readable error message
            details: Additional context (server, database, driver)

        """
        super().__init__(
            message=message,
            error_code="CONNECTION_ERROR",
            details=details,
        )


class QueryError(MSSQLMCPError):
    """SQL query execution failed.

    Raised when a query fails during execution.
    Common causes: syntax error, permission denied, timeout.
    """

    def __init__(
        self,
        message: str,
        query: str | None = None,
        details: dict[str, str] | None = None,
    ):
        """Initialize query error.

        Args:
            message: Human-readable error message
            query: The SQL query that failed
            details: Additional context

        """
        error_details = details or {}
        if query:
            error_details["query"] = query[:200]  # Truncate long queries
        super().__init__(
            message=message,
            error_code="QUERY_ERROR",
            details=error_details,
        )


class SecurityError(MSSQLMCPError):
    """Query blocked by security filtering.

    Raised when a query is rejected because it contains
    dangerous operations (INSERT, UPDATE, DELETE, etc.).
    """

    def __init__(
        self,
        message: str,
        query: str | None = None,
        blocked_keyword: str | None = None,
    ):
        """Initialize security error.

        Args:
            message: Human-readable error message
            query: The blocked query
            blocked_keyword: The dangerous keyword that triggered the block

        """
        details: dict[str, str] = {}
        if query:
            details["query"] = query[:200]
        if blocked_keyword:
            details["blocked_keyword"] = blocked_keyword
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            details=details,
        )


class ValidationError(MSSQLMCPError):
    """Invalid input parameters.

    Raised when tool parameters fail validation.
    Common causes: empty strings, invalid types, out-of-range values.
    """

    def __init__(
        self,
        message: str,
        parameter: str | None = None,
        value: str | None = None,
    ):
        """Initialize validation error.

        Args:
            message: Human-readable error message
            parameter: The parameter that failed validation
            value: The invalid value (truncated if too long)

        """
        details: dict[str, str] = {}
        if parameter:
            details["parameter"] = parameter
        if value:
            details["value"] = str(value)[:100]
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class TimeoutError(MSSQLMCPError):
    """Query or connection timeout.

    Raised when a database operation exceeds the configured timeout.
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize timeout error.

        Args:
            message: Human-readable error message
            operation: The operation that timed out
            timeout_seconds: The configured timeout value

        """
        details: dict[str, str] = {}
        if operation:
            details["operation"] = operation
        if timeout_seconds is not None:
            details["timeout_seconds"] = str(timeout_seconds)
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=details,
        )


def format_error_response(error: Exception) -> str:
    """Format an error as JSON for MCP response.

    Args:
        error: The exception to format

    Returns:
        JSON string with error details

    """
    import json

    if isinstance(error, MSSQLMCPError):
        return json.dumps(error.to_dict(), indent=2)

    # For non-MSSQLMCPError exceptions, create a generic error response
    return json.dumps(
        {
            "error": "INTERNAL_ERROR",
            "message": str(error),
            "details": {"type": error.__class__.__name__},
        },
        indent=2,
    )


# Transient error codes that should trigger retry logic
# Based on pyodbc error codes and SQL Server error numbers
TRANSIENT_ERROR_CODES = {
    "08S01",  # Communication link failure
    "08001",  # Unable to connect to data source
    "HYT00",  # Timeout expired
    "HYT01",  # Connection timeout expired
    "40001",  # Serialization failure (deadlock)
    "40197",  # SQL Azure: Service temporarily unavailable
    "40501",  # SQL Azure: Service is busy
    "40613",  # SQL Azure: Database unavailable
    "49918",  # SQL Azure: Cannot process request
    "49919",  # SQL Azure: Cannot process create/update request
    "49920",  # SQL Azure: Cannot process delete request
}


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should be retried.

    Args:
        error: The exception to check

    Returns:
        True if error is transient, False otherwise

    """
    import pyodbc

    if not isinstance(error, pyodbc.Error):
        return False

    # Check if error code is in transient list
    if hasattr(error, "args") and len(error.args) > 0:
        error_code = str(error.args[0])
        return error_code in TRANSIENT_ERROR_CODES

    return False
