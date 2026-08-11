from pydantic import BaseModel

class CommandResult(BaseModel):
    command: str 
    success: bool  
    output: str       

class ValidationResult(BaseModel):
    seed: CommandResult
    run: CommandResult | None  
    test: CommandResult | None  
    success: bool