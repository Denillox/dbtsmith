from dbtsmith.introspect.csv import get_table_schema


def test_get_table_schema_sample_orders():
    """Deterministic — reads a real file, but no network/database
    dependency, unlike the Postgres introspection tests."""
    schema = get_table_schema("tests/fixtures/sample_orders.csv")

    assert schema.table_name == "sample_orders"

    types_by_name = {col.name: col.data_type for col in schema.columns}
    assert types_by_name["id"] == "integer"
    assert types_by_name["customer_id"] == "integer"
    assert types_by_name["order_total"] == "numeric"
    assert types_by_name["email"] == "text"
    assert types_by_name["order_date"] == "text"