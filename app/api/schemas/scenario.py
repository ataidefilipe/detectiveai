from pydantic import BaseModel
from typing import List, Optional


class ScenarioListItem(BaseModel):
    id: int
    title: str
    description: Optional[str]


class ScenarioDetailResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    suspects: List[dict]
    evidences: List[dict]
