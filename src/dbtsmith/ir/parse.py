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