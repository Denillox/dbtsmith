import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from dbtsmith.ir.input import ParsedInput
from dbtsmith.ir.models import Step, StepList, TransformationIR, Source, Output
from dbtsmith.introspect.models import TableSchema
from dbtsmith.introspect.postgres import get_table_schema as get_postgres_schema
from dbtsmith.introspect.csv import get_table_schema as get_csv_schema

def _is_csv(source: str) -> bool:
    return source.endswith(".csv")

def _build_prompt(instruction: str, schemas: list[TableSchema]) -> str:
    prompt = ""
    for schema in schemas:
        prompt += f'Table "{schema.table_name}" has these columns:'
        for col in schema.columns:
            prompt += f'\n- {col.name} ({col.data_type})'
        prompt += '\n\n'

    prompt += f'Instruction: {instruction}\n\n'
    prompt += (
        'Given this schema and instruction, produce the ordered list of '
        'transformation steps. For aggregation steps, when grouping by a '
        'time period (e.g. "by month"), set the group_by column to the '
        'real date/timestamp column name and set granularity to "day", '
        '"month", or "year" — do not write raw SQL expressions.'
        'For dedupe steps, always inlcude "order_by" - a real column'
        'name to use for determining which duplicate to keep'
    )

    return prompt


def parse_instruction(parsed_input: ParsedInput) -> TransformationIR:
    load_dotenv()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )

    structured_llm = llm.with_structured_output(StepList)
    is_csv = _is_csv(parsed_input.source_table)

    if is_csv:
        source_schema = get_csv_schema(parsed_input.source_table)
    else:
        source_schema = get_postgres_schema(parsed_input.source_table)

    join_schemas = [get_postgres_schema(t) for t in parsed_input.join_targets]
    schemas = [source_schema] + join_schemas

    prompt = _build_prompt(parsed_input.instruction, schemas)
    result = structured_llm.invoke(prompt)

    source_type = "csv" if is_csv else "postgres_table"

    return TransformationIR(
        source=Source(type=source_type, identifier=parsed_input.source_table),
        transformations=result.steps,
        output=Output(name=parsed_input.output_name),
    )


def parse_instruction_with_feedback(
    parsed_input: ParsedInput,
    previous_ir: TransformationIR,
    failure_output: str,
) -> TransformationIR:
    load_dotenv()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    structured_llm = llm.with_structured_output(StepList)

    is_csv = _is_csv(parsed_input.source_table)
    source_schema = get_csv_schema(parsed_input.source_table) if is_csv else get_postgres_schema(parsed_input.source_table)
    join_schemas = [get_postgres_schema(t) for t in parsed_input.join_targets]
    schemas = [source_schema] + join_schemas

    base_prompt = _build_prompt(parsed_input.instruction, schemas)

    previous_steps_json = previous_ir.model_dump_json(include={"transformations"})

    feedback_prompt = (
        f"{base_prompt}\n\n"
        "A previous attempt at this instruction produced the following "
        f"steps, but failed validation:\n{previous_steps_json}\n\n"
        f"The validation failure was:\n{failure_output[-1500:]}\n\n"
        "Produce a corrected ordered list of transformation steps that "
        "still fulfills the original instruction above, but avoids the "
        "cause of this specific failure. Do not simply remove steps to "
        "avoid the error — only change what's actually wrong."
    )

    result = structured_llm.invoke(feedback_prompt)
    source_type = "csv" if is_csv else "postgres_table"

    return TransformationIR(
        source=Source(type=source_type, identifier=parsed_input.source_table),
        transformations=result.steps,
        output=Output(name=parsed_input.output_name),
    )