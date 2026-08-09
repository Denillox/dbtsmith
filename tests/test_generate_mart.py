import pytest

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.mart import generate_mart_model


def _make_ir(**overrides):
    base = dict(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "email", "right_column": "email"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "order_date", "granularity": "month"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total_orders"}
                ],
            },
        ],
        output={"name": "monthly_customer_orders"},
    )
    base.update(overrides)
    return TransformationIR(**base)


def test_generate_mart_model():
    ir = _make_ir()
    sql = generate_mart_model(ir)

    assert "ref('stg_orders')" in sql
    assert "INNER JOIN" in sql
    assert "source('dbtsmith_output', 'customers')" in sql
    assert "o.email = c.email" in sql
    assert "DATE_TRUNC('month', o.order_date) AS order_date_month" in sql
    assert "SUM(o.order_total) AS total_orders" in sql


def test_generate_mart_model_requires_join_and_aggregate():
    """Missing join or aggregate should fail loudly, not guess."""
    ir = _make_ir(transformations=[])

    with pytest.raises(ValueError):
        generate_mart_model(ir)