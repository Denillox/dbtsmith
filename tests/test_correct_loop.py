import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from dbtsmith.ir.input import ParsedInput
from dbtsmith.correct.loop import generate_with_correction

load_dotenv()


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires GROQ_API_KEY and network access — not run in CI.",
)
def test_generate_with_correction_succeeds_first_attempt(tmp_path):
    """The standard worked example should succeed on attempt 1 —
    proving the loop works correctly even when no retry is needed."""
    parsed_input = ParsedInput(
        source_table="orders",
        instruction="dedupe by email, join with customers, aggregate order totals by month",
        output_name="monthly_customer_orders",
        join_targets=["customers"],
    )

    final_state = generate_with_correction(parsed_input, tmp_path, max_attempts=2)

    assert final_state["validation_result"].success is True
    assert final_state["attempt"] == 1
    assert len(final_state["history"]) == 1