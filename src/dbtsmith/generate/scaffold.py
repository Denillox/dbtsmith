"""
Generates the non-model parts of a complete, self-contained dbt
project: dbt_project.yml, profiles.yml, and sources.yml — everything
needed for `dbt run`/`dbt test` to work in a fresh output directory
with nothing hand-authored in advance.
"""

from pathlib import Path
import yaml
import shutil

from dbtsmith.ir.models import TransformationIR, JoinStep

DBT_PROJECT_YML = """\
name: dbtsmith_output
version: "1.0.0"
config-version: 2

profile: dbtsmith_output

model-paths: ["models"]

models:
  dbtsmith_output:
    staging:
      +materialized: view
    marts:
      +materialized: table
"""

PROFILES_YML = """\
dbtsmith_output:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST') }}"
      port: "{{ env_var('POSTGRES_PORT') | int }}"
      user: "{{ env_var('POSTGRES_USER') }}"
      password: "{{ env_var('POSTGRES_PASSWORD') }}"
      dbname: "{{ env_var('POSTGRES_DB') }}"
      schema: public
      threads: 1
"""


def _get_all_source_tables(ir: TransformationIR) -> list[str]:
    tables = []

    if ir.source.type == "postgres_table":
        tables.append(ir.source.identifier)

    for step in ir.transformations:
        if isinstance(step, JoinStep):
            tables.append(step.target)

    return tables


def _generate_sources_yml(ir: TransformationIR) -> str:
    schema_dict = {
        "version": 2,
        "sources": [
            {
                "name": "dbtsmith_output",
                "schema": "public",
                "tables": [{"name": t} for t in _get_all_source_tables(ir)],
            }
        ],
    }
    return yaml.dump(schema_dict, sort_keys=False)


def scaffold_project(ir: TransformationIR, output_dir: Path) -> None:
    """Create a complete, empty dbt project structure at output_dir —
    ready for staging/mart/schema files to be written into it."""
    (output_dir / "models" / "staging").mkdir(parents=True, exist_ok=True)
    (output_dir / "models" / "marts").mkdir(parents=True, exist_ok=True)
    (output_dir / "seeds").mkdir(parents=True, exist_ok=True)

    (output_dir / "dbt_project.yml").write_text(DBT_PROJECT_YML)
    (output_dir / "profiles.yml").write_text(PROFILES_YML)

    sources_yml = _generate_sources_yml(ir)
    (output_dir / "models" / "staging" / "sources.yml").write_text(sources_yml)

    if ir.source.type == "csv":
        csv_path = Path(ir.source.identifier)
        shutil.copy(csv_path, output_dir / "seeds" / csv_path.name)