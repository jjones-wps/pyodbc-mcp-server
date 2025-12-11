# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
