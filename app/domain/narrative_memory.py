"""
narrative_memory.py

Schemas Pydantic para a memória narrativa da sessão do suspeito.
Compreende:
1. Memória Relacional: registro conciso de eventos interpessoais com o detetive.
2. Ledger de Flavor: escolhas cosméticas autoradas e congeladas na sessão.
"""

from typing import Literal, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MemorySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlavorEntry(MemorySchema):
    slot_key: str = Field(min_length=1, max_length=64)
    option_id: str = Field(min_length=1, max_length=64)
    established_by_npc_message_id: Optional[int] = Field(default=None)


class RelationalEvent(MemorySchema):
    kind: Literal[
        "player_pressured",
        "player_calmed",
        "player_offered_protection",
        "npc_requested_protection",
        "npc_committed",
    ]
    source_message_id: Optional[int] = Field(default=None)
    topic_id: Optional[str] = None


class SessionNarrativeMemory(MemorySchema):
    version: int = 1
    events: List[RelationalEvent] = Field(default_factory=list, max_length=12)
    flavor: List[FlavorEntry] = Field(default_factory=list, max_length=8)
