from pydantic import BaseModel
from typing import Optional

class PlayerChatInput(BaseModel):
    text: str
    evidence_id: Optional[int] = None
