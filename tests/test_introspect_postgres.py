from dbtsmith.introspect.postgres import get_table_schema


def test_get_table_schema_orders():
    # Requires the local Postgres dev container to be running (docker compose up -d) with the sample schema from the project README/setup notes loaded.
    schema = get_table_schema("orders")

    assert schema.table_name == "orders"

    column_names = {col.name for col in schema.columns}
    assert column_names == {"id", "customer_id", "order_total", "order_date", "email", "product_id"}

    types_by_name = {col.name: col.data_type for col in schema.columns}
    assert types_by_name["id"] == "integer"
    assert types_by_name["order_total"] == "numeric"