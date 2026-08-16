from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, model_validator


# ── Source ───────────────────────────────────────────────────────────────

class Source(BaseModel):
    # Where the data comes from
    type: Literal["postgres_table", "csv"]
    identifier: str


# ── Transformation steps ────────────────────────────────────────────────

class DedupeStep(BaseModel):
    # Remove duplicate rows based on one or more key columns
    type: Literal["dedupe"] = "dedupe"
    keys: list[str]
    keep: Literal["first", "last"]
    order_by: str


class JoinKey(BaseModel):
    # One column pair a join is performed on
    left_column: str
    right_column: str


class JoinStep(BaseModel):
    # Join the current data against another table/source
    type: Literal["join"] = "join"
    target: str
    on: list[JoinKey]
    how: Literal["inner", "left"]

class Aggregation(BaseModel):
    column: str
    table: str | None = None
    function: Literal["sum", "count", "avg"]
    alias: str


class GroupByColumn(BaseModel):
    column: str
    table: str | None = None
    granularity: Literal["day", "month", "year"] | None = None


class AggregateStep(BaseModel):
    type: Literal["aggregate"] = "aggregate"
    group_by: list[GroupByColumn]
    aggregations: list[Aggregation]


Step = Annotated[
    Union[DedupeStep, JoinStep, AggregateStep],
    Field(discriminator="type"),
]

class StepList(BaseModel):
    steps: list[Step]

# ── Output ───────────────────────────────────────────────────────────────

class Output(BaseModel):
    # The resulting dbt mart this transformation produces
    name: str


class TransformationIR(BaseModel):
    source: Source
    transformations: list[Step]
    output: Output

    @model_validator(mode="after")
    def validate_table_references(self) -> "TransformationIR":
        join_targets = {
            step.target for step in self.transformations if isinstance(step, JoinStep)
        }

        for step in self.transformations:
            if isinstance(step, AggregateStep):
                for group_col in step.group_by:
                    if group_col.table is not None and group_col.table not in join_targets:
                        raise ValueError(
                            f"GroupByColumn references table '{group_col.table}', "
                            f"but no JoinStep targets it."
                        )
                for agg in step.aggregations:
                    if agg.table is not None and agg.table not in join_targets:
                        raise ValueError(
                            f"Aggregation references table '{agg.table}', "
                            f"but no JoinStep targets it."
                        )

        return self