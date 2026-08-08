from pydantic import BaseModel, Field

class ParsedInput(BaseModel):
    source_table: str
    instruction: str
    output_name: str
    join_targets: list[str] = Field(default_factory=list)