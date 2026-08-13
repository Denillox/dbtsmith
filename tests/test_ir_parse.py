import os

import pytest
from dotenv import load_dotenv

from dbtsmith.ir.input import ParsedInput
from dbtsmith.ir.parse import parse_instruction, parse_instruction_with_feedback
from dbtsmith.ir.models import TransformationIR

load_dotenv()


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires GROQ_API_KEY and network access — not run in CI.",
)
def test_parse_instruction_worked_example():
    """
    Real LLM call — output isn't deterministic, so this checks
    structure and validity, not exact values.
    """
    parsed_input = ParsedInput(
        source_table="orders",
        instruction="dedupe by email, join with customers, aggregate order totals by month",
        output_name="monthly_customer_orders",
        join_targets=["customers"],
    )

    ir = parse_instruction(parsed_input)

    assert len(ir.transformations) == 3
    assert ir.transformations[0].type == "dedupe"
    assert ir.transformations[1].type == "join"
    assert ir.transformations[2].type == "aggregate"

    assert "email" in ir.transformations[0].keys

    aggregate_step = ir.transformations[2]
    assert any(g.granularity == "month" for g in aggregate_step.group_by)


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires GROQ_API_KEY and network access — not run in CI.",
)
def test_parse_instruction_with_feedback_corrects_bad_join():
    parsed_input = ParsedInput(
        source_table="orders",
        instruction="dedupe by email, join with customers, aggregate order totals by month",
        output_name="monthly_customer_orders",
        join_targets=["customers"],
    )

    previous_ir = TransformationIR(
        source={"type": "postgres_table", "identifier": "orders"},
        transformations=[
            {"type": "dedupe", "keys": ["email"], "keep": "first", "order_by": "id"},
            {
                "type": "join",
                "target": "customers",
                "on": [{"left_column": "customer_id", "right_column": "customer_ref"}],
                "how": "inner",
            },
            {
                "type": "aggregate",
                "group_by": [{"column": "order_date", "granularity": "month"}],
                "aggregations": [
                    {"column": "order_total", "function": "sum", "alias": "total_order_value"}
                ],
            },
        ],
        output={"name": "monthly_customer_orders"},
    )

    failure_output = (
        "Database Error in model monthly_customer_orders\n"
        "  column c.customer_ref does not exist\n"
        "  LINE 5:     ON o.customer_id = c.customer_ref"
    )

    corrected_ir = parse_instruction_with_feedback(parsed_input, previous_ir, failure_output)

    join_step = corrected_ir.transformations[1]
    assert join_step.type == "join"
    assert join_step.on[0].right_column != "customer_ref"


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires GROQ_API_KEY and network access — not run in CI.",
)
def test_parse_instruction_with_feedback_does_not_weaken_correct_ir():
    """A failure caused by a genuine data problem (not a wrong IR)
    should NOT cause the dedupe step to be dropped or weakened — the
    correction should recognize there's nothing structurally wrong to
    fix, and leave the plan intact."""
    parsed_input = ParsedInput(
        source_table="orders",
        instruction="dedupe by email, join with customers, aggregate order totals by month",
        output_name="monthly_customer_orders",
        join_targets=["customers"],
    )

    previous_ir = TransformationIR(
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
                    {"column": "order_total", "function": "sum", "alias": "total_order_value"}
                ],
            },
        ],
        output={"name": "monthly_customer_orders"},
    )

    failure_output = (
        "[ERROR]: in test not_null_stg_orders_email (models\\schema.yml)\n"
        "  Got 1 result, configured to fail if != 0\n"
    )

    corrected_ir = parse_instruction_with_feedback(parsed_input, previous_ir, failure_output)

    dedupe_step = corrected_ir.transformations[0]
    assert dedupe_step.type == "dedupe"
    assert "email" in dedupe_step.keys