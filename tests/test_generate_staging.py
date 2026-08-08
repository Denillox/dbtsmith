from dbtsmith.ir.models import TransformationIR
from dbtsmith.introspect.models import ColumnInfo, TableSchema
from dbtsmith.generate.staging import generate_staging_model


def test_generate_staging_model_with_dedupe():
    """
    Generated SQL should reflect the dedupe step's real keys and
    order_by — checking structure, not exact text, since template
    formatting details could reasonably change later.
    """
    ir = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
        ],
        output={"name": "monthly_customer_orders"},
    )
    schema = TableSchema(
        table_name="orders",
        columns=[
            ColumnInfo(name="id", data_type="integer"),
            ColumnInfo(name="email", data_type="text"),
            ColumnInfo(name="order_total", data_type="numeric"),
        ],
    )

    sql = generate_staging_model(ir, schema)

    assert "PARTITION BY email" in sql
    assert "ORDER BY id" in sql
    assert "ROW_NUMBER()" in sql
    assert "source('dbtsmith_output', 'orders')" in sql
    assert "order_total" in sql
    assert "rn\n" not in sql.split("FROM (")[0] 