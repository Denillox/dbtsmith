import os

import pytest
from dotenv import load_dotenv

from dbtsmith.ir.input import ParsedInput
from dbtsmith.ir.parse import parse_instruction

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