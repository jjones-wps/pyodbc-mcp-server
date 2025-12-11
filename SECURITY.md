# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model

This MCP server is designed with security as a primary concern for database access:

### Read-Only by Design

- **SELECT only**: Only queries starting with `SELECT` are allowed
- **Keyword blocking**: Dangerous SQL keywords are blocked even in subqueries:
  - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`
  - `EXEC`, `EXECUTE`, `TRUNCATE`, `GRANT`, `REVOKE`, `DENY`
  - `BACKUP`, `RESTORE`, `SHUTDOWN`, `DBCC`

### Authentication

- **Windows Authentication only**: Uses `Trusted_Connection=yes`
- **No credential storage**: No passwords stored in configuration
- **Domain security**: Leverages existing Windows/Active Directory security

### Resource Protection

- **Row limiting**: Maximum 1000 rows per query (configurable, default 100)
- **No network exposure**: stdio transport only (no HTTP endpoints)
- **Query validation**: All queries validated before execution

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. **Email**: Send details to the repository owner privately
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Resolution target**: Within 30 days for critical issues

## Security Best Practices for Users

When deploying this MCP server:

1. **Least privilege**: Grant only SELECT permissions to the Windows account
2. **Network isolation**: Run on machines with direct SQL Server access
3. **Audit logging**: Enable SQL Server audit logging for the service account
4. **Regular updates**: Keep dependencies updated (especially pyodbc)

## Known Limitations

- Keyword blocking is pattern-based and may not catch all edge cases
- Windows Authentication requires the server to run under a domain account
- No query complexity analysis (expensive queries are not blocked)

## Security Updates

Security updates will be released as patch versions (e.g., 0.1.1, 0.1.2).

Subscribe to repository releases to be notified of security updates.
