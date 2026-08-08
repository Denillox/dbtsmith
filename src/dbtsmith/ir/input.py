from pydantic import BaseModel

class ParsedInput(BaseModel):
    """
    What the user supplies, three labeled fields. The `instruction` field 
    is the only part that stays natural language; everything the LLM needs to
    figure out lives there.
    """

    source_table: str
    instruction: str
    output_name: str