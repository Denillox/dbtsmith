import yaml

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.schema import generate_schema_yml


def _make_ir():
    return TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
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


def test_generate_schema_yml():
    ir = _make_ir()
    yml_text = generate_schema_yml(ir)

    parsed = yaml.safe_load(yml_text)

    assert parsed["version"] == 2
    models_by_name = {m["name"]: m for m in parsed["models"]}

    staging = models_by_name["stg_orders"]
    email_column = staging["columns"][0]
    assert email_column["name"] == "email"
    assert set(email_column["tests"]) == {"not_null", "unique"}

    mart = models_by_name["monthly_customer_orders"]
    group_column = mart["columns"][0]
    assert group_column["name"] == "order_date_month"
    assert group_column["tests"] == ["not_null"]


def test_generate_schema_yml_no_mart():
    """No join/aggregate steps present -> schema.yml should only
    include the staging entry, not reference a mart that will never
    be generated."""
    ir = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
        ],
        output={"name": "some_output"},
    )
    yml_text = generate_schema_yml(ir)
    parsed = yaml.safe_load(yml_text)

    assert len(parsed["models"]) == 1
    assert parsed["models"][0]["name"] == "stg_orders"