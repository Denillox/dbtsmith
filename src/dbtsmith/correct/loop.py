from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END

from dbtsmith.ir.input import ParsedInput
from dbtsmith.ir.parse import parse_instruction, parse_instruction_with_feedback
from dbtsmith.ir.models import TransformationIR
from dbtsmith.introspect.postgres import get_table_schema as get_postgres_schema
from dbtsmith.introspect.csv import get_table_schema as get_csv_schema
from dbtsmith.generate.scaffold import scaffold_project
from dbtsmith.generate.staging import generate_staging_model, staging_model_name
from dbtsmith.generate.mart import generate_mart_model, ir_has_mart
from dbtsmith.generate.schema import generate_schema_yml
from dbtsmith.validate.dbt import validate_project
from dbtsmith.validate.models import ValidationResult


class CorrectionState(TypedDict):
    parsed_input: ParsedInput
    output_dir: Path
    attempt: int
    max_attempts: int
    ir: TransformationIR | None
    validation_result: ValidationResult | None
    history: list[dict]


def _failure_output(result: ValidationResult) -> str:
    """The most relevant failure text — same precedence cli.py/app.py
    already use: test output if it ran, else run output, else seed."""
    if result.test is not None:
        return result.test.output
    if result.run is not None:
        return result.run.output
    return result.seed.output


def parse_node(state: CorrectionState) -> dict:
    attempt = state["attempt"] + 1

    if attempt == 1:
        ir = parse_instruction(state["parsed_input"])
    else:
        ir = parse_instruction_with_feedback(
            state["parsed_input"],
            state["ir"],
            _failure_output(state["validation_result"]),
        )

    return {"ir": ir, "attempt": attempt}


def generate_node(state: CorrectionState) -> dict:
    ir = state["ir"]
    output_dir = state["output_dir"]
    source = state["parsed_input"].source_table

    if source.endswith(".csv"):
        schema = get_csv_schema(source)
    else:
        schema = get_postgres_schema(source)

    scaffold_project(ir, output_dir)

    staging_sql = generate_staging_model(ir, schema)
    staging_path = output_dir / "models" / "staging" / f"{staging_model_name(ir)}.sql"
    staging_path.write_text(staging_sql)

    if ir_has_mart(ir):
        mart_sql = generate_mart_model(ir)
        mart_path = output_dir / "models" / "marts" / f"{ir.output.name}.sql"
        mart_path.write_text(mart_sql)

    schema_yml = generate_schema_yml(ir)
    schema_path = output_dir / "models" / "schema.yml"
    schema_path.write_text(schema_yml)

    return {}


def validate_node(state: CorrectionState) -> dict:
    result = validate_project(state["output_dir"])

    history_entry = {
        "attempt": state["attempt"],
        "ir": state["ir"].model_dump(),
        "success": result.success,
        "output": _failure_output(result) if not result.success else "passed",
    }

    return {
        "validation_result": result,
        "history": state["history"] + [history_entry],
    }


def _should_retry(state: CorrectionState) -> str:
    if state["validation_result"].success:
        return "end"
    if state["attempt"] >= state["max_attempts"]:
        return "end"
    return "retry"


# --- Graph construction ---

_graph = StateGraph(CorrectionState)
_graph.add_node("parse", parse_node)
_graph.add_node("generate", generate_node)
_graph.add_node("validate", validate_node)

_graph.set_entry_point("parse")
_graph.add_edge("parse", "generate")
_graph.add_edge("generate", "validate")
_graph.add_conditional_edges("validate", _should_retry, {"retry": "parse", "end": END})

_compiled_graph = _graph.compile()


def generate_with_correction(
    parsed_input: ParsedInput,
    output_dir: Path,
    max_attempts: int = 2,
) -> CorrectionState:
    """Run the full parse -> generate -> validate loop, retrying with
    LLM feedback on failure, up to max_attempts total attempts."""
    initial_state: CorrectionState = {
        "parsed_input": parsed_input,
        "output_dir": output_dir,
        "attempt": 0,
        "max_attempts": max_attempts,
        "ir": None,
        "validation_result": None,
        "history": [],
    }
    return _compiled_graph.invoke(initial_state)