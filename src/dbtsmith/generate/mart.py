from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from dbtsmith.ir.models import TransformationIR, JoinStep, AggregateStep, GroupByColumn
from dbtsmith.generate.staging import staging_model_name

TEMPLATES_DIR = Path(__file__).parent.parent / "dbt_templates"


def _get_join_steps(ir: TransformationIR) -> list[JoinStep]:
    steps = []
    for step in ir.transformations:
        if isinstance(step, JoinStep):
            steps.append(step)
    return steps


def _get_aggregate_step(ir: TransformationIR) -> AggregateStep | None:
    for step in ir.transformations:
        if isinstance(step, AggregateStep):
            return step
    return None


def _build_join_clauses(join_steps: list[JoinStep]) -> str:
    how_map = {"inner": "INNER JOIN", "left": "LEFT JOIN"}

    clauses = []
    for join_step in join_steps:
        how_sql = how_map[join_step.how]
        source_ref = f"{{{{ source('dbtsmith_output', '{join_step.target}') }}}}"
        alias = join_step.target
        key = join_step.on[0]
        clause = f"{how_sql} {source_ref} {alias}\n    ON o.{key.left_column} = {alias}.{key.right_column}"
        clauses.append(clause)

    return "\n".join(clauses)


def _build_group_by_expr(aggregate_step: AggregateStep) -> str:
    group_col = aggregate_step.group_by[0]
    if group_col.granularity is not None:
        return f"DATE_TRUNC('{group_col.granularity}', o.{group_col.column})"
    return f"o.{group_col.column}"


def group_by_alias(group_col: GroupByColumn) -> str:
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


def ir_has_mart(ir: TransformationIR) -> bool:
    return len(_get_join_steps(ir)) > 0


def generate_mart_model(ir: TransformationIR) -> str:
    join_steps = _get_join_steps(ir)
    aggregate_step = _get_aggregate_step(ir)

    if not join_steps or aggregate_step is None:
        raise ValueError(
            "Mart generation requires at least one JoinStep and "
            "exactly one AggregateStep in the TransformationIR."
        )

    ref_expr = f"{{{{ ref('{staging_model_name(ir)}') }}}}"

    join_clauses = _build_join_clauses(join_steps)
    group_by_expr = _build_group_by_expr(aggregate_step)
    select_columns = _build_select_columns(aggregate_step, group_by_expr)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("mart_model.sql.jinja")

    return template.render(
        select_columns=select_columns,
        ref_expr=ref_expr,
        join_clauses=join_clauses,
        group_by_expr=group_by_expr,
    )