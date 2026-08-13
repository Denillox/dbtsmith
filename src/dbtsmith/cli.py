"""
CLI entrypoint for dbtsmith — chains parsing, introspection,
generation, and validation into one command.
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from dbtsmith.ir.input import ParsedInput
from dbtsmith.ir.parse import parse_instruction
from dbtsmith.introspect.postgres import get_table_schema as get_postgres_schema
from dbtsmith.introspect.csv import get_table_schema as get_csv_schema
from dbtsmith.generate.scaffold import scaffold_project
from dbtsmith.generate.staging import generate_staging_model, staging_model_name
from dbtsmith.generate.mart import generate_mart_model, ir_has_mart
from dbtsmith.generate.schema import generate_schema_yml
from dbtsmith.validate.dbt import validate_project
from dbtsmith.correct.loop import generate_with_correction


@click.command()
@click.option("--source", prompt="Source table", help="The Postgres table to transform.")
@click.option("--instruction", prompt="Instruction", help="Natural language description of the transformation.")
@click.option("--output", prompt="Output mart name", help="Name of the resulting dbt mart.")
@click.option("--join", "join_targets", multiple=True, help="Table(s) this instruction joins against. Repeatable.")
@click.option("--output-dir", default="./dbtsmith_output", type=click.Path(path_type=Path), help="Where to write the generated dbt project.")
@click.option("--allow-retry", is_flag=True, help="Retry with LLM feedback if validation fails.")
def generate(source, instruction, output, join_targets, output_dir, allow_retry):
    """Turn a natural-language instruction into a validated dbt project."""
    load_dotenv()

    parsed_input = ParsedInput(
        source_table=source,
        instruction=instruction,
        output_name=output,
        join_targets=list(join_targets),
    )

    if allow_retry:
        click.echo("Running with self-correction enabled (up to 2 attempts)...")
        final_state = generate_with_correction(parsed_input, output_dir, max_attempts=2)
        result = final_state["validation_result"]

        if final_state["attempt"] > 1:
            click.echo(f"\nRequired {final_state['attempt']} attempts:")
            for entry in final_state["history"]:
                status = "passed" if entry["success"] else "failed"
                click.echo(f"  Attempt {entry['attempt']}: {status}")
    else:
        click.echo("Parsing instruction...")
        ir = parse_instruction(parsed_input)

        click.echo("Introspecting source schema...")
        if source.endswith(".csv"):
            schema = get_csv_schema(source)
        else:
            schema = get_postgres_schema(source)

        click.echo(f"Scaffolding project at {output_dir}...")
        scaffold_project(ir, output_dir)

        click.echo("Generating staging model...")
        staging_sql = generate_staging_model(ir, schema)
        (output_dir / "models" / "staging" / f"{staging_model_name(ir)}.sql").write_text(staging_sql)

        if ir_has_mart(ir):
            click.echo("Generating mart model...")
            mart_sql = generate_mart_model(ir)
            (output_dir / "models" / "marts" / f"{output}.sql").write_text(mart_sql)
        else:
            click.echo("No join/aggregate steps — skipping mart generation.")

        click.echo("Generating schema.yml...")
        schema_yml = generate_schema_yml(ir)
        (output_dir / "models" / "schema.yml").write_text(schema_yml)

        click.echo("Validating generated project...")
        result = validate_project(output_dir)

    if result.success:
        click.echo("Success — generated project passed dbt seed, dbt run, and dbt test.")
    else:
        click.echo("Validation failed.")
        if result.test is not None:
            click.echo(result.test.output)
        elif result.run is not None:
            click.echo(result.run.output)
        else:
            click.echo(result.seed.output)
        sys.exit(1)