"""
Streamlit UI for dbtsmith — a form-based front end over the same
pipeline the CLI uses: parse_instruction -> introspect -> scaffold ->
generate -> validate.
"""

import streamlit as st
from pathlib import Path
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

load_dotenv()

if __name__ == "__main__":
    st.set_page_config(page_title="dbtsmith", page_icon="🛠️")
    st.title("dbtsmith")
    st.caption("Turn a natural-language instruction into a validated dbt project")

    with st.form("generate_form"):
        source = st.text_input("Source table or CSV path", placeholder="orders")
        instruction = st.text_area(
            "Instruction",
            placeholder="dedupe by email, join with customers, aggregate order totals by month",
        )
        output = st.text_input("Output mart name", placeholder="monthly_customer_orders")
        join_targets_raw = st.text_input(
            "Join targets (comma-separated, optional)", placeholder="customers"
        )
        output_dir = st.text_input("Output directory", value="./streamlit_output")
        allow_retry = st.checkbox("Allow retry with LLM feedback on failure")

        submitted = st.form_submit_button("Generate")

    if submitted:
        join_targets = [t.strip() for t in join_targets_raw.split(",") if t.strip()]
        output_path = Path(output_dir)

        parsed_input = ParsedInput(
            source_table=source,
            instruction=instruction,
            output_name=output,
            join_targets=join_targets,
        )

        if allow_retry:
            with st.status("Running pipeline with self-correction...", expanded=True) as status:
                final_state = generate_with_correction(parsed_input, output_path, max_attempts=2)
                result = final_state["validation_result"]

                for entry in final_state["history"]:
                    outcome = "passed" if entry["success"] else "failed"
                    st.write(f"Attempt {entry['attempt']}: {outcome}")

                if result.success:
                    status.update(label="Success!", state="complete")
                else:
                    status.update(label="Validation failed", state="error")

            if final_state["attempt"] > 1:
                st.info(f"Required {final_state['attempt']} attempts — see log above.")

            ir = final_state["ir"]
        else:
            with st.status("Running pipeline...", expanded=True) as status:
                st.write("Parsing instruction...")
                ir = parse_instruction(parsed_input)

                st.write("Introspecting source schema...")
                if source.endswith(".csv"):
                    schema = get_csv_schema(source)
                else:
                    schema = get_postgres_schema(source)

                st.write(f"Scaffolding project at {output_path}...")
                scaffold_project(ir, output_path)

                st.write("Generating staging model...")
                staging_sql = generate_staging_model(ir, schema)
                staging_path = output_path / "models" / "staging" / f"{staging_model_name(ir)}.sql"
                staging_path.write_text(staging_sql)

                if ir_has_mart(ir):
                    st.write("Generating mart model...")
                    mart_sql = generate_mart_model(ir)
                    mart_path = output_path / "models" / "marts" / f"{output}.sql"
                    mart_path.write_text(mart_sql)
                else:
                    st.write("No join/aggregate steps — skipping mart generation.")

                st.write("Generating schema.yml...")
                schema_yml = generate_schema_yml(ir)
                schema_path = output_path / "models" / "schema.yml"
                schema_path.write_text(schema_yml)

                st.write("Validating generated project...")
                result = validate_project(output_path)

                if result.success:
                    status.update(label="Success!", state="complete")
                else:
                    status.update(label="Validation failed", state="error")

        # --- Shared display logic, regardless of which path ran ---
        if result.success:
            st.success("Generated project passed dbt seed, dbt run, and dbt test.")
        else:
            st.error("Validation failed.")
            if result.test is not None:
                st.code(result.test.output)
            elif result.run is not None:
                st.code(result.run.output)
            else:
                st.code(result.seed.output)

        staging_file = output_path / "models" / "staging" / f"{staging_model_name(ir)}.sql"
        if staging_file.exists():
            st.subheader("Generated staging model")
            st.code(staging_file.read_text(), language="sql")

        mart_file = output_path / "models" / "marts" / f"{output}.sql"
        if mart_file.exists():
            st.subheader("Generated mart model")
            st.code(mart_file.read_text(), language="sql")

        schema_file = output_path / "models" / "schema.yml"
        if schema_file.exists():
            st.subheader("Generated schema.yml")
            st.code(schema_file.read_text(), language="yaml")