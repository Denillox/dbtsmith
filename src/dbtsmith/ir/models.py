from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


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
    # One computed column in an aggregate step, e.g. SUM(order_total) AS total
    column: str
    # Constrained to a small known set of functions for v1, enough to cover the worked example (sum) plus the other common cases.
    function: Literal["sum", "count", "avg"]
    alias: str


class AggregateStep(BaseModel):
    # Group rows and compute aggregate values per group
    type: Literal["aggregate"] = "aggregate"
    group_by: list[str]
    aggregations: list[Aggregation]


Step = Annotated[
    Union[DedupeStep, JoinStep, AggregateStep],
    Field(discriminator="type"),
]


# ── Output ───────────────────────────────────────────────────────────────

class Output(BaseModel):
    # The resulting dbt mart this transformation produces
    name: str


# ── The top-level IR ─────────────────────────────────────────────────────

class TransformationIR(BaseModel):
    source: Source
    transformations: list[Step]

    output: Output