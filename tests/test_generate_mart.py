import pytest

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.mart import generate_mart_model
from dbtsmith.generate.scaffold import scaffold_project
from dbtsmith.generate.staging import staging_model_name, generate_staging_model
from dbtsmith.generate.schema import generate_schema_yml
from dbtsmith.introspect.postgres import get_table_schema
from dbtsmith.validate.dbt import validate_project


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
    assert "o.email = customers.email" in sql
    assert "DATE_TRUNC('month', o.order_date) AS order_date_month" in sql
    assert "SUM(o.order_total) AS total_orders" in sql


def test_generate_mart_model_requires_join_and_aggregate():
    """Missing join or aggregate should fail loudly, not guess."""
    ir = _make_ir(transformations=[])

    with pytest.raises(ValueError):
        generate_mart_model(ir)


def test_generate_mart_model_multiple_joins():
    ir = _make_ir(
        transformations=[
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "email", "right_column": "email"}],
                "how": "inner",
            },
            {
                "type": "join",
                "target": "products",
                "on": [{"left_column": "product_id", "right_column": "id"}],
                "how": "left",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "order_date", "granularity": "month"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total_orders"}
                ],
            },
        ],
    )
    sql = generate_mart_model(ir)

    assert "INNER JOIN" in sql
    assert "LEFT JOIN" in sql
    assert "source('dbtsmith_output', 'customers')" in sql
    assert "source('dbtsmith_output', 'products')" in sql
    assert "o.email = customers.email" in sql
    assert "o.product_id = products.id" in sql


def test_multi_join_mart_validates_against_real_data(tmp_path):
    """Real end-to-end proof: a two-join IR should actually build and
    pass dbt test against real Postgres data — not just produce
    plausible-looking SQL."""
    ir = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "customer_id", "right_column": "id"}],
                "how": "inner",
            },
            {
                "type": "join",
                "target": "products",
                "on": [{"left_column": "product_id", "right_column": "id"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "order_date", "granularity": "month"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total"}
                ],
            },
        ],
        output={"name": "multi_join_test_mart"},
    )
    schema = get_table_schema("orders")
    scaffold_project(ir, tmp_path)

    staging_sql = generate_staging_model(ir, schema)
    staging_path = tmp_path / "models" / "staging" / f"{staging_model_name(ir)}.sql"
    staging_path.write_text(staging_sql)

    mart_sql = generate_mart_model(ir)
    mart_path = tmp_path / "models" / "marts" / f"{ir.output.name}.sql"
    mart_path.write_text(mart_sql)

    schema_yml = generate_schema_yml(ir)
    schema_path = tmp_path / "models" / "schema.yml"
    schema_path.write_text(schema_yml)

    result = validate_project(tmp_path)
    assert result.success is True


def test_generate_mart_model_multi_column_group_by():
    ir = _make_ir(
        transformations=[
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "email", "right_column": "email"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [
                    {"column": "order_date", "granularity": "month"},
                    {"column": "product_id", "granularity": None},
                ],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total_orders"}
                ],
            },
        ],
    )
    sql = generate_mart_model(ir)

    assert "DATE_TRUNC('month', o.order_date) AS order_date_month" in sql
    assert "o.product_id AS product_id" in sql
    assert "GROUP BY DATE_TRUNC('month', o.order_date), o.product_id" in sql


def test_generate_mart_model_joined_table_column():
    ir = _make_ir(
        transformations=[
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "customer_id", "right_column": "id"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "region", "table": "customers"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total"}
                ],
            },
        ],
    )
    sql = generate_mart_model(ir)

    assert "customers.region AS region" in sql
    assert "GROUP BY customers.region" in sql
    assert "SUM(o.order_total) AS total" in sql