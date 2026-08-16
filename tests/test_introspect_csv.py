from dbtsmith.introspect.csv import get_table_schema, _looks_like_date
import pandas as pd


def test_get_table_schema_sample_orders():
    schema = get_table_schema("tests/fixtures/sample_orders.csv")

    assert schema.table_name == "sample_orders"

    types_by_name = {col.name: col.data_type for col in schema.columns}
    assert types_by_name["id"] == "integer"
    assert types_by_name["customer_id"] == "integer"
    assert types_by_name["order_total"] == "numeric"
    assert types_by_name["email"] == "text"
    assert types_by_name["order_date"] == "date"


def test_looks_like_date_rejects_numeric_strings():
    assert _looks_like_date(pd.Series(["1", "2", "3"])) is False


def test_looks_like_date_rejects_plain_text():
    assert _looks_like_date(pd.Series(["Alice", "Bob", "Carol"])) is False


def test_looks_like_date_accepts_iso_dates():
    assert _looks_like_date(pd.Series(["2025-01-15", "2025-02-03"])) is True


def test_looks_like_date_handles_nulls():
    assert _looks_like_date(pd.Series(["2025-01-15", None, "2025-02-03"])) is True