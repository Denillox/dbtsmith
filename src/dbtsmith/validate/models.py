from pydantic import BaseModel

class CommandResult(BaseModel):
    command: str 
    success: bool  
    output: str       

class ValidationResult(BaseModel):
    run: CommandResult
    test: CommandResult | None
    success: bool