from pydantic import BaseModel, Field
from typing import Optional, List
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
