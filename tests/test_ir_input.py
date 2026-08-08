from dbtsmith.ir.input import ParsedInput


def test_parsed_input_construction():
    """The lightly-structured user input should construct cleanly from
    the worked example in the project brief."""
    parsed = ParsedInput(
        source_table="orders",
        instruction="dedupe by email, join with customers, aggregate order totals by month",
        output_name="monthly_customer_orders",
    )

    assert parsed.source_table == "orders"
    assert parsed.output_name == "monthly_customer_orders"
    assert "dedupe" in parsed.instruction