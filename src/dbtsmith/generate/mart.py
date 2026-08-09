"""
Generates a dbt mart model SQL file from a TransformationIR's join
and aggregate steps, building on top of the staging model.

v1 scope: assumes exactly one JoinStep and one AggregateStep, in that
order. Multiple joins/aggregates, or other orderings, are out of scope
for now.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from dbtsmith.ir.models import TransformationIR, JoinStep, AggregateStep, GroupByColumn

TEMPLATES_DIR = Path(__file__).parent.parent / "dbt_templates"


def _get_join_step(ir: TransformationIR) -> JoinStep | None:
    for step in ir.transformations:
        if isinstance(step, JoinStep):
            return step
    return None


def _get_aggregate_step(ir: TransformationIR) -> AggregateStep | None:
    for step in ir.transformations:
        if isinstance(step, AggregateStep):
            return step
    return None


def _build_join_clause(join_step: JoinStep) -> str:
    how_map = {"inner": "INNER JOIN", "left": "LEFT JOIN"}
    how_sql = how_map[join_step.how]

    source_ref = f"{{{{ source('dbtsmith_output', '{join_step.target}') }}}}"

    key = join_step.on[0]
    condition = f"o.{key.left_column} = c.{key.right_column}"

    return f"{how_sql} {source_ref} c\n    ON {condition}"


def _build_group_by_expr(aggregate_step: AggregateStep) -> str:
    group_col = aggregate_step.group_by[0]

    if group_col.granularity is not None:
        return f"DATE_TRUNC('{group_col.granularity}', o.{group_col.column})"
    else:
        return f"o.{group_col.column}"


def group_by_alias(group_col: GroupByColumn) -> str:
    """The column name the group-by expression ends up aliased as in
    the generated SQL — shared with schema.py so tests stay in sync
    with what's actually generated."""
    if group_col.granularity is not None:
        return f"{group_col.column}_{group_col.granularity}"
    return group_col.column


def _build_select_columns(aggregate_step: AggregateStep, group_by_expr: str) -> str:
    alias = group_by_alias(aggregate_step.group_by[0])
    lines = [f"{group_by_expr} AS {alias}"]

    for agg in aggregate_step.aggregations:
        func_sql = agg.function.upper()
        lines.append(f"{func_sql}(o.{agg.column}) AS {agg.alias}")

    return ",\n    ".join(lines)

def generate_mart_model(ir: TransformationIR) -> str:
    """Render the mart model SQL for this IR's join + aggregate steps."""
    join_step = _get_join_step(ir)
    aggregate_step = _get_aggregate_step(ir)

    if join_step is None or aggregate_step is None:
        raise ValueError(
            "Mart generation requires exactly one JoinStep and one "
            "AggregateStep in the TransformationIR (v1 scope limitation)."
        )

    ref_expr = f"{{{{ ref('stg_{ir.source.identifier}') }}}}"
    join_clause = _build_join_clause(join_step)
    group_by_expr = _build_group_by_expr(aggregate_step)
    select_columns = _build_select_columns(aggregate_step, group_by_expr)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("mart_model.sql.jinja")

    return template.render(
        select_columns=select_columns,
        ref_expr=ref_expr,
        join_clause=join_clause,
        group_by_expr=group_by_expr,
    )