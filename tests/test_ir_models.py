from dbtsmith.ir.models import TransformationIR


def test_transformation_ir_round_trip():
    ir = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first"},
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "customer_id", "right_column": "id"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": ["month"],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total_order_value"}
                ],
            },
        ],
        output={"name": "monthly_customer_orders"},
    )

    assert ir.source.identifier == "orders"
    assert len(ir.transformations) == 3
    assert ir.transformations[0].type == "dedupe"
    assert ir.transformations[1].type == "join"
    assert ir.transformations[2].type == "aggregate"
    assert ir.output.name == "monthly_customer_orders"