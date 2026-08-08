from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from dbtsmith.ir.models import TransformationIR, DedupeStep
from dbtsmith.introspect.models import TableSchema

TEMPLATES_DIR = Path(__file__).parent.parent / "dbt_templates"


def _get_dedupe_step(ir: TransformationIR) -> DedupeStep | None:
    for step in ir.transformations:
        if isinstance(step, DedupeStep):
            return step
    return None

def generate_staging_model(ir: TransformationIR, schema: TableSchema) -> str:
    """Render the staging model SQL for this IR's source table."""
    dedupe_step = _get_dedupe_step(ir)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("staging_model.sql.jinja")


    source_ref = f"{{{{ source('dbtsmith_output', '{ir.source.identifier}') }}}}"

    columns = [col.name for col in schema.columns]

    if dedupe_step is None:
        column_list = ",\n    ".join(columns)
        return f"SELECT\n    {column_list}\nFROM {source_ref}"

    return template.render(
        columns=columns,
        dedupe_keys=dedupe_step.keys,
        order_by=dedupe_step.order_by,
        source_ref=source_ref,
    )