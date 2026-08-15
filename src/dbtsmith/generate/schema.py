import yaml

from dbtsmith.ir.models import TransformationIR
from dbtsmith.generate.staging import _get_dedupe_step, staging_model_name
from dbtsmith.generate.mart import _get_aggregate_step, group_by_alias, ir_has_mart


def _staging_model_entry(ir: TransformationIR) -> dict:
    dedupe_step = _get_dedupe_step(ir)
    name = staging_model_name(ir)

    if dedupe_step is None:
        return {"name": name, "columns": []}

    return {
        "name": name,
        "columns": [
            {"name": key, "tests": ["not_null", "unique"]}
            for key in dedupe_step.keys
        ],
    }

def _mart_model_entry(ir: TransformationIR) -> dict:
    aggregate_step = _get_aggregate_step(ir)

    if aggregate_step is None:
        return {"name": ir.output.name, "columns": []}

    columns = [
        {"name": group_by_alias(group_col), "tests": ["not_null"]}
        for group_col in aggregate_step.group_by
    ]

    return {
        "name": ir.output.name,
        "columns": columns,
    }


def generate_schema_yml(ir: TransformationIR) -> str:
    models = [_staging_model_entry(ir)]

    if ir_has_mart(ir):
        models.append(_mart_model_entry(ir))

    schema_dict = {
        "version": 2,
        "models": models,
    }

    return yaml.dump(schema_dict, sort_keys=False)