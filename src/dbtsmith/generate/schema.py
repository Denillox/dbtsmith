import yaml

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.staging import _get_dedupe_step
from dbtsmith.generate.mart import _get_join_step, _get_aggregate_step, group_by_alias


def _staging_model_entry(ir: TransformationIR) -> dict:
    dedupe_step = _get_dedupe_step(ir)

    if dedupe_step is None:
        return {"name": f"stg_{ir.source.identifier}", "columns": []}

    return {
        "name": f"stg_{ir.source.identifier}",
        "columns": [
            {"name": key, "tests": ["not_null", "unique"]}
            for key in dedupe_step.keys
        ],
    }


def _mart_model_entry(ir: TransformationIR) -> dict:
    aggregate_step = _get_aggregate_step(ir)

    if aggregate_step is None:
        return {"name": ir.output.name, "columns": []}

    group_col = aggregate_step.group_by[0]
    alias = group_by_alias(group_col)

    return {
        "name": ir.output.name,
        "columns": [
            {"name": alias, "tests": ["not_null"]},
        ],
    }


def generate_schema_yml(ir: TransformationIR) -> str:
    """Render the full schema.yml content as a YAML string."""
    schema_dict = {
        "version": 2,
        "models": [
            _staging_model_entry(ir),
            _mart_model_entry(ir),
        ],
    }

    return yaml.dump(schema_dict, sort_keys=False)