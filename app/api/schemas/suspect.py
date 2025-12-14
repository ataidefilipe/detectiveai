from pydantic import BaseModel
from typing import Optional


class SuspectSessionResponse(BaseModel):
    suspect_id: int
    name: str
    backstory: Optional[str]
    initial_statement: Optional[str] 
    progress: float
    is_closed: bool
