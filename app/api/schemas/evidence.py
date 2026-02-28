from pydantic import BaseModel

class EvidenceResponse(BaseModel):
    id: int
    name: str
    description: str | None
