"""
Typed representation of a real source's schema — what introspection
functions return, and what the generation step will be grounded in.
"""

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    """One column's name and type, as reported by the real source."""
    name: str
    data_type: str


class TableSchema(BaseModel):
    """The full introspected schema of one table."""
    table_name: str
    columns: list[ColumnInfo]