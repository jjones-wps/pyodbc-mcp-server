"""Pytest configuration and shared fixtures for MSSQL MCP Server tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest


class MockRow:
    """Mock database row with attribute access."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize mock row with column values."""
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = MagicMock()
    cursor.description = None
    cursor.rowcount = 0
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Create a mock database connection with cursor."""
    connection = MagicMock()
    connection.cursor.return_value = mock_cursor
    return connection


@pytest.fixture
def sample_tables():
    """Sample table data for testing ListTables."""
    return [
        MockRow(TABLE_SCHEMA="dbo", TABLE_NAME="users"),
        MockRow(TABLE_SCHEMA="dbo", TABLE_NAME="orders"),
        MockRow(TABLE_SCHEMA="sales", TABLE_NAME="customers"),
    ]


@pytest.fixture
def sample_columns():
    """Sample column data for testing DescribeTable."""
    return [
        MockRow(
            COLUMN_NAME="id",
            DATA_TYPE="int",
            IS_NULLABLE="NO",
            CHARACTER_MAXIMUM_LENGTH=None,
            NUMERIC_PRECISION=10,
            NUMERIC_SCALE=0,
            COLUMN_DEFAULT=None,
        ),
        MockRow(
            COLUMN_NAME="username",
            DATA_TYPE="varchar",
            IS_NULLABLE="NO",
            CHARACTER_MAXIMUM_LENGTH=50,
            NUMERIC_PRECISION=None,
            NUMERIC_SCALE=None,
            COLUMN_DEFAULT=None,
        ),
        MockRow(
            COLUMN_NAME="email",
            DATA_TYPE="varchar",
            IS_NULLABLE="YES",
            CHARACTER_MAXIMUM_LENGTH=255,
            NUMERIC_PRECISION=None,
            NUMERIC_SCALE=None,
            COLUMN_DEFAULT="'noreply@example.com'",
        ),
    ]


@pytest.fixture
def sample_primary_keys():
    """Sample primary key data for testing DescribeTable enhancements."""
    return [MockRow(COLUMN_NAME="id")]


@pytest.fixture
def sample_foreign_keys():
    """Sample foreign key data for testing DescribeTable enhancements."""
    return [
        MockRow(
            column_name="user_id",
            ref_schema="dbo",
            ref_table="users",
            ref_column="id",
        )
    ]


@pytest.fixture
def sample_indexes():
    """Sample index data for testing ListIndexes."""
    return [
        MockRow(
            index_name="PK_users",
            index_type="CLUSTERED",
            is_unique=True,
            is_primary_key=True,
            columns="id",
        ),
        MockRow(
            index_name="IX_users_email",
            index_type="NONCLUSTERED",
            is_unique=True,
            is_primary_key=False,
            columns="email",
        ),
    ]


@pytest.fixture
def sample_constraints():
    """Sample constraint data for testing ListConstraints."""
    return [
        MockRow(
            CONSTRAINT_NAME="CK_users_age",
            CONSTRAINT_TYPE="CHECK",
            COLUMN_NAME="age",
            CHECK_CLAUSE="([age]>=(18))",
        ),
        MockRow(
            CONSTRAINT_NAME="UQ_users_email",
            CONSTRAINT_TYPE="UNIQUE",
            COLUMN_NAME="email",
            CHECK_CLAUSE="",
        ),
        MockRow(
            CONSTRAINT_NAME="DF_users_created_at",
            CONSTRAINT_TYPE="DEFAULT",
            COLUMN_NAME="created_at",
            CHECK_CLAUSE="",
        ),
    ]


@pytest.fixture
def sample_procedures():
    """Sample stored procedure data for testing ListStoredProcedures."""
    return [
        MockRow(
            schema_name="dbo",
            procedure_name="sp_GetUserById",
            parameters="@UserId int",
        ),
        MockRow(
            schema_name="sales",
            procedure_name="sp_CalculateTotal",
            parameters="@OrderId int, @DiscountRate decimal",
        ),
        MockRow(
            schema_name="dbo",
            procedure_name="sp_DeleteOldRecords",
            parameters=None,
        ),
    ]


@pytest.fixture
def sample_functions():
    """Sample user-defined function data for testing ListFunctions."""
    return [
        MockRow(
            schema_name="dbo",
            function_name="fn_CalculateDiscount",
            function_type="SQL_SCALAR_FUNCTION",
            parameters="@Amount decimal, @Rate decimal",
        ),
        MockRow(
            schema_name="sales",
            function_name="fn_GetTopCustomers",
            function_type="SQL_INLINE_TABLE_VALUED_FUNCTION",
            parameters="@TopN int",
        ),
        MockRow(
            schema_name="dbo",
            function_name="fn_GetUserRoles",
            function_type="SQL_TABLE_VALUED_FUNCTION",
            parameters="@UserId int",
        ),
    ]


@pytest.fixture
def sample_triggers():
    """Sample trigger data for testing ListTriggers."""
    return [
        MockRow(
            schema_name="dbo",
            trigger_name="trg_UpdateTimestamp",
            table_name="users",
            trigger_type="AFTER",
            is_disabled=0,
            events="UPDATE",
        ),
        MockRow(
            schema_name="sales",
            trigger_name="trg_AuditChanges",
            table_name="orders",
            trigger_type="AFTER",
            is_disabled=0,
            events="INSERT, UPDATE, DELETE",
        ),
        MockRow(
            schema_name="dbo",
            trigger_name="trg_InsteadOfDelete",
            table_name="archive",
            trigger_type="INSTEAD OF",
            is_disabled=1,
            events="DELETE",
        ),
    ]


@pytest.fixture
def sample_outgoing_fks():
    """Sample outgoing foreign key data for testing GetTableRelationships."""
    return [
        MockRow(
            constraint_name="FK_orders_customer_id",
            referenced_schema="dbo",
            referenced_table="customers",
            column_name="customer_id",
            referenced_column="id",
            on_delete="NO_ACTION",
            on_update="CASCADE",
            is_disabled=0,
            constraint_column_id=1,
        )
    ]


@pytest.fixture
def sample_incoming_fks():
    """Sample incoming foreign key data for testing GetTableRelationships."""
    return [
        MockRow(
            constraint_name="FK_order_items_order_id",
            referencing_schema="dbo",
            referencing_table="order_items",
            referencing_column="order_id",
            referenced_column="id",
            on_delete="CASCADE",
            on_update="NO_ACTION",
            is_disabled=0,
            constraint_column_id=1,
        )
    ]


@pytest.fixture
def sample_composite_fk():
    """Sample composite foreign key data for testing composite FK support."""
    return [
        MockRow(
            constraint_name="FK_order_items_product",
            referenced_schema="dbo",
            referenced_table="inventory",
            column_name="product_id",
            referenced_column="product_id",
            on_delete="NO_ACTION",
            on_update="NO_ACTION",
            is_disabled=0,
            constraint_column_id=1,
        ),
        MockRow(
            constraint_name="FK_order_items_product",
            referenced_schema="dbo",
            referenced_table="inventory",
            column_name="warehouse_id",
            referenced_column="warehouse_id",
            on_delete="NO_ACTION",
            on_update="NO_ACTION",
            is_disabled=0,
            constraint_column_id=2,
        ),
    ]
