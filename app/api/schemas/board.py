from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class BoardNodeSchema(BaseModel):
    id: str
    type: str  # "suspect" | "evidence"
    ref_id: int
    title: str
    subtitle: Optional[str] = None
    image_url: Optional[str] = None
    x: float
    y: float


class BoardConnectionSchema(BaseModel):
    id: Optional[str] = None
    from_id: str
    to_id: str
    label: Optional[str] = None


class BoardStickerSchema(BaseModel):
    id: str
    text: str = ""
    color: str = "yellow"  # "yellow" | "pink" | "blue"
    x: float
    y: float


class BoardDataSchema(BaseModel):
    nodes: List[BoardNodeSchema] = Field(default_factory=list)
    connections: List[BoardConnectionSchema] = Field(default_factory=list)
    stickers: List[BoardStickerSchema] = Field(default_factory=list)


class BoardStateResponse(BaseModel):
    session_id: int
    board_data: BoardDataSchema
    updated_at: Optional[datetime] = None


class SaveBoardStateRequest(BaseModel):
    board_data: BoardDataSchema


BoardConnectionStatus = Literal[
    "supported_by_facts",
    "plausible_unproven",
    "contradicted_by_facts",
    "vague",
]


class EvaluateBoardRequest(BaseModel):
    board_data: Optional[BoardDataSchema] = None


class BoardConnectionEvaluationSchema(BaseModel):
    connection_id: Optional[str] = None
    from_id: str
    to_id: str
    label: Optional[str] = None
    status: BoardConnectionStatus
    confidence: float = 0.0


class BoardEvaluationResponse(BaseModel):
    session_id: int
    provider: str
    connections: List[BoardConnectionEvaluationSchema] = Field(default_factory=list)
    summary: str
    latency_ms: int = 0
    fallback_reason: Optional[str] = None
