# Código Completo do Projeto

*Gerado automaticamente em 14/12/2025 às 15:22*

Total de arquivos: 35

---

## Arquivo: `app/__init__.py`

```python
# App package

if __name__ == "__main__":
    from .main import start_app
    start_app()
```

---

## Arquivo: `app/__main__.py`

```python
"""Main execution entry point for the detective AI app."""

from .main import start_app

if __name__ == "__main__":
    start_app()
```

---

## Arquivo: `app/api/__init__.py`

```python
# API package
```

---

## Arquivo: `app/api/scenarios.py`

```python
from fastapi import APIRouter, HTTPException
from typing import List

from app.infra.db import SessionLocal
from app.infra.db_models import ScenarioModel, SuspectModel, EvidenceModel
from app.api.schemas.scenario import (
    ScenarioListItem,
    ScenarioDetailResponse
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# -----------------------------
# GET /scenarios
# -----------------------------
@router.get("", response_model=List[ScenarioListItem])
def list_scenarios():
    db = SessionLocal()
    try:
        scenarios = db.query(ScenarioModel).all()

        return [
            ScenarioListItem(
                id=s.id,
                title=s.title,
                description=s.description
            )
            for s in scenarios
        ]
    finally:
        db.close()


# -----------------------------
# GET /scenarios/{id} (opcional)
# -----------------------------
@router.get("/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario_detail(scenario_id: int):
    db = SessionLocal()
    try:
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == scenario_id
        ).first()

        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        suspects = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == scenario_id
        ).all()

        evidences = db.query(EvidenceModel).filter(
            EvidenceModel.scenario_id == scenario_id
        ).all()

        return ScenarioDetailResponse(
            id=scenario.id,
            title=scenario.title,
            description=scenario.description,
            suspects=[
                {"id": s.id, "name": s.name}
                for s in suspects
            ],
            evidences=[
                {
                    "id": e.id,
                    "name": e.name,
                    "description": e.description,
                    "is_mandatory": e.id in (scenario.required_evidence_ids or [])
                }
                for e in evidences
            ]
        )

    finally:
        db.close()
```

---

## Arquivo: `app/api/schemas/chat.py`

```python
from pydantic import BaseModel
from typing import Optional

class PlayerChatInput(BaseModel):
    text: str
    evidence_id: Optional[int] = None
```

---

## Arquivo: `app/api/schemas/evidence.py`

```python
from pydantic import BaseModel

class EvidenceResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_mandatory: bool
```

---

## Arquivo: `app/api/schemas/scenario.py`

```python
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
```

---

## Arquivo: `app/api/schemas/suspect.py`

```python
from pydantic import BaseModel
from typing import Optional


class SuspectSessionResponse(BaseModel):
    suspect_id: int
    name: str
    backstory: Optional[str]
    initial_statement: Optional[str] 
    progress: float
    is_closed: bool
```

---

## Arquivo: `app/api/schemas/verdict.py`

```python
from pydantic import BaseModel
from typing import List


class AccuseRequest(BaseModel):
    suspect_id: int
    evidence_ids: List[int]


class AccuseResponse(BaseModel):
    session_id: int
    status: str
    result_type: str
    chosen_suspect_id: int
    real_culprit_id: int
    required_evidence_ids: List[int]
    missing_evidence_ids: List[int]
    description: str
```

---

## Arquivo: `app/api/sessions.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from app.api.schemas.chat import PlayerChatInput
from app.api.schemas.verdict import AccuseRequest, AccuseResponse
from app.api.schemas.evidence import EvidenceResponse
from app.api.schemas.suspect import SuspectSessionResponse

from app.services.chat_service import add_player_message, add_npc_reply
from app.services.secret_service import apply_evidence_to_suspect
from app.services.session_finalize_service import finalize_session
from app.services.session_service import create_session, get_session_overview, get_suspect_state

from app.infra.db import SessionLocal
from app.infra.db_models import NpcChatMessageModel, SessionModel, SessionSuspectStateModel, SuspectModel, ScenarioModel, EvidenceModel


router = APIRouter()


# -----------------------------
# Request schema
# -----------------------------
class CreateSessionRequest(BaseModel):
    scenario_id: int


# -----------------------------
# Response schema
# -----------------------------
class CreateSessionResponse(BaseModel):
    session_id: int
    scenario_id: int
    status: str


# -----------------------------
# POST /sessions
# -----------------------------
@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(payload: CreateSessionRequest):
    try:
        session_data = create_session(payload.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateSessionResponse(
        session_id=session_data["id"],
        scenario_id=session_data["scenario_id"],
        status=session_data["status"]
    )

@router.post("/sessions/{session_id}/suspects/{suspect_id}/messages")
def send_message_to_suspect(session_id: int, suspect_id: int, payload: PlayerChatInput):
    """
    Handles a full interrogation turn:
    - save player message
    - apply evidence (if any)
    - generate NPC reply
    - return everything combined
    """

    # 1. Player message
    player_msg = add_player_message(
        session_id=session_id,
        suspect_id=suspect_id,
        text=payload.text,
        evidence_id=payload.evidence_id
    )

    # 2. Evidence logic (may reveal secrets)
    revealed_secrets = []
    if payload.evidence_id is not None:
        revealed_secrets = apply_evidence_to_suspect(
            session_id=session_id,
            suspect_id=suspect_id,
            evidence_id=payload.evidence_id
        )

    # 3. NPC reply
    npc_msg = add_npc_reply(
        session_id=session_id,
        suspect_id=suspect_id,
        player_message_id=player_msg["id"]
    )

    # 4. Fetch updated suspect state (snapshot for UX)
    suspect_state = get_suspect_state(
        session_id=session_id,
        suspect_id=suspect_id
    )

    # 5. Output combined response
    return {
        "player_message": player_msg,
        "npc_message": npc_msg,
        "revealed_secrets": revealed_secrets,
        "suspect_state": suspect_state
    }


@router.post(
    "/sessions/{session_id}/accuse",
    response_model=AccuseResponse
)
def accuse_session(session_id: int, payload: AccuseRequest):
    """
    Finalizes a session by accusing a suspect with selected evidences.
    """

    db = SessionLocal()
    try:
        # ----------------------------------------
        # 1. Finalize session
        # ----------------------------------------
        result = finalize_session(
            session_id=session_id,
            chosen_suspect_id=payload.suspect_id,
            evidence_ids=payload.evidence_ids,
            db=db
        )

        verdict = result["verdict"]

        # ----------------------------------------
        # 2. Basic description (non-AI)
        # ----------------------------------------
        if verdict["result_type"] == "correct":
            description = (
                "Você identificou corretamente o culpado e apresentou todas "
                "as evidências essenciais."
            )
        elif verdict["result_type"] == "partial":
            description = (
                "Você identificou corretamente o culpado, mas deixou passar "
                "evidências essenciais."
            )
        else:
            description = (
                "O suspeito acusado não é o verdadeiro culpado."
            )

        # ----------------------------------------
        # 3. Build response
        # ----------------------------------------
        return AccuseResponse(
            session_id=result["session_id"],
            status=result["status"],
            result_type=verdict["result_type"],
            chosen_suspect_id=verdict["chosen_suspect_id"],
            real_culprit_id=verdict["real_culprit_id"],
            required_evidence_ids=verdict["required_evidence_ids"],
            missing_evidence_ids=verdict["missing_evidence_ids"],
            description=description
        )

    finally:
        db.close()



# -----------------------------
# NEW: GET /sessions/{session_id}
# -----------------------------

class SessionOverviewResponse(BaseModel):
    session: dict
    scenario: dict
    suspects: list


@router.get("/sessions/{session_id}", response_model=SessionOverviewResponse)
def api_get_session_overview(session_id: int):
    try:
        overview = get_session_overview(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # get_session_overview já retorna progress e is_closed por suspeito
    return overview

@router.get("/sessions/{session_id}/suspects/{suspect_id}/status")
def get_suspect_status(session_id: int, suspect_id: int):
    db = SessionLocal()
    try:
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise HTTPException(status_code=404, detail="Suspect not found in this session.")

        return {
            "suspect_id": state.suspect_id,
            "progress": state.progress,
            "is_closed": state.is_closed
        }

    finally:
        db.close()




class ChatMessageResponse(BaseModel):
    id: int
    sender_type: str
    text: str
    evidence_id: int | None
    timestamp: str

@router.get("/sessions/{session_id}/suspects/{suspect_id}/messages",
            response_model=List[ChatMessageResponse])
def get_chat_messages(session_id: int, suspect_id: int):
    """
    Returns the chronological chat history between the player and the suspect
    in the given session.
    """

    db = SessionLocal()

    try:
        # 1. Ensure session exists
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

        # 2. Ensure suspect belongs to scenario of the session
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id,
            SuspectModel.scenario_id == session.scenario_id
        ).first()

        if not suspect:
            raise HTTPException(
                status_code=404,
                detail=f"Suspect {suspect_id} not found in scenario {session.scenario_id}."
            )

        # 3. Load chronological chat history
        messages = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id
        ).order_by(NpcChatMessageModel.timestamp.asc()).all()

        # 4. Serialize for output
        result = [
            ChatMessageResponse(
                id=m.id,
                sender_type=m.sender_type,
                text=m.text,
                evidence_id=m.evidence_id,
                timestamp=m.timestamp.isoformat()
            )
            for m in messages
        ]

        return result

    finally:
        db.close()


@router.get(
    "/sessions/{session_id}/evidences",
    response_model=list[EvidenceResponse]
)
def get_session_evidences(session_id: int):
    db = SessionLocal()
    try:
        # 1. Buscar sessão
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 2. Buscar evidências do cenário
        evidences = db.query(EvidenceModel).filter(
            EvidenceModel.scenario_id == session.scenario_id
        ).all()

        # 3. Mapear obrigatórias
        mandatory_ids = session.scenario.required_evidence_ids

        return [
            EvidenceResponse(
                id=e.id,
                name=e.name,
                description=e.description,
                is_mandatory=e.id in mandatory_ids
            )
            for e in evidences
        ]

    finally:
        db.close()

@router.get(
    "/sessions/{session_id}/suspects",
    response_model=list[SuspectSessionResponse]
)
def list_session_suspects(session_id: int):
    db = SessionLocal()
    try:
        # 1. Validar sessão
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 2. Buscar suspeitos do cenário
        suspects = db.query(SuspectModel).filter(
            SuspectModel.scenario_id == session.scenario_id
        ).all()

        # 3. Buscar estados da sessão
        states = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id
        ).all()

        state_map = {s.suspect_id: s for s in states}

        # 4. Montar resposta
        return [
            SuspectSessionResponse(
                suspect_id=s.id,
                name=s.name,
                backstory=s.backstory,
                initial_statement=s.initial_statement,
                progress=state_map[s.id].progress if s.id in state_map else 0.0,
                is_closed=state_map[s.id].is_closed if s.id in state_map else False
            )
            for s in suspects
        ]

    finally:
        db.close()
```

---

## Arquivo: `app/domain/__init__.py`

```python
# Domain package
```

---

## Arquivo: `app/domain/models.py`

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Scenario(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., description="Title of the scenario")
    description: Optional[str] = None
    culprit_id: Optional[int] = None  # ID of the guilty suspect

class Suspect(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    name: str = Field(..., description="Name of the suspect")
    backstory: Optional[str] = None

class Evidence(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    name: str = Field(..., description="Name of the evidence")
    description: Optional[str] = None

class Secret(BaseModel):
    id: Optional[int] = None
    suspect_id: int
    evidence_id: int
    content: str = Field(..., description="Secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class Session(BaseModel):
    id: Optional[int] = None
    scenario_id: int
    status: str = Field(default="in_progress", description="Session status")
    created_at: datetime = Field(default_factory=datetime.now)

class SessionSuspectState(BaseModel):
    session_id: int
    suspect_id: int
    revealed_secret_ids: List[int] = Field(default_factory=list)
    is_closed: bool = Field(default=False)
    progress: float = Field(default=0.0)

class NpcChatMessage(BaseModel):
    id: Optional[int] = None
    session_id: int
    suspect_id: int
    sender_type: str = Field(..., description="player or npc")
    text: str = Field(..., description="Message content")
    evidence_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionEvidenceUsage(BaseModel):
    session_id: int
    suspect_id: int
    evidence_id: int
    used_at: datetime = Field(default_factory=datetime.now)
```

---

## Arquivo: `app/domain/schema_scenario.py`

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class SecretConfig(BaseModel):
    suspect: str = Field(..., description="Name of the suspect this secret belongs to")
    evidence: str = Field(..., description="Name of the evidence that reveals this secret")
    content: str = Field(..., description="The secret information")
    is_core: bool = Field(default=False, description="Whether this is a core secret for progress")

class SuspectConfig(BaseModel):
    name: str
    backstory: Optional[str] = None
    initial_statement: Optional[str] = Field(
        default=None,
        description="Initial statement shown to the player before interrogation"
    )
    final_phrase: Optional[str] = Field(
        default="I've told you everything I know."
    )


class EvidenceConfig(BaseModel):
    name: str = Field(..., description="Name of the evidence")
    description: Optional[str] = None
    is_mandatory: bool = Field(default=False, description="Whether this evidence is required for correct verdict")

class ChronologyEvent(BaseModel):
    time: str = Field(..., description="Timestamp or description of the event time")
    description: str = Field(..., description="Description of the event")

class ScenarioConfig(BaseModel):
    title: str = Field(..., description="Title of the scenario")
    description: Optional[str] = None
    culprit: str = Field(..., description="Name of the guilty suspect")
    suspects: List[SuspectConfig] = Field(..., description="List of suspects")
    evidences: List[EvidenceConfig] = Field(..., description="List of evidences")
    secrets: List[SecretConfig] = Field(..., description="List of secrets")
    chronology: Optional[List[ChronologyEvent]] = None
```

---

## Arquivo: `app/infra/__init__.py`

```python
# Infrastructure package
```

---

## Arquivo: `app/infra/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .db_models import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./game.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
```

---

## Arquivo: `app/infra/db_models.py`

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList

Base = declarative_base()

class ScenarioModel(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    case_summary = Column(String)
    culprit_id = Column(Integer)  # Not FK, as it's a reference to Suspect

    required_evidence_ids = Column(
        MutableList.as_mutable(JSON), default=list
    )

    partial_evidence_ids = Column(
        MutableList.as_mutable(JSON), default=list
    )

    suspects = relationship("SuspectModel", back_populates="scenario")
    evidences = relationship("EvidenceModel", back_populates="scenario")
    sessions = relationship("SessionModel", back_populates="scenario")

class SuspectModel(Base):
    __tablename__ = "suspects"
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    name = Column(String, nullable=False)
    backstory = Column(String)
    initial_statement = Column(String)
    final_phrase = Column(String, nullable=True)
    true_timeline = Column(JSON) 
    lies = Column(JSON)          

    scenario = relationship("ScenarioModel", back_populates="suspects")
    secrets = relationship("SecretModel", back_populates="suspect")
    session_states = relationship("SessionSuspectStateModel", back_populates="suspect")
    chat_messages = relationship("NpcChatMessageModel", back_populates="suspect")
    evidence_usages = relationship("SessionEvidenceUsageModel", back_populates="suspect")

class EvidenceModel(Base):
    __tablename__ = "evidences"
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

    scenario = relationship("ScenarioModel", back_populates="evidences")
    secrets = relationship("SecretModel", back_populates="evidence")
    evidence_usages = relationship("SessionEvidenceUsageModel", back_populates="evidence")

class SecretModel(Base):
    __tablename__ = "secrets"
    id = Column(Integer, primary_key=True, index=True)
    suspect_id = Column(Integer, ForeignKey("suspects.id"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidences.id"), nullable=False)
    content = Column(String, nullable=False)
    is_core = Column(Boolean, default=False)

    suspect = relationship("SuspectModel", back_populates="secrets")
    evidence = relationship("EvidenceModel", back_populates="secrets")

class SessionModel(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    status = Column(String, default="in_progress")
    created_at = Column(DateTime, default=datetime.now)
    chosen_suspect_id = Column(Integer, nullable=True)
    chosen_evidence_ids = Column(
        MutableList.as_mutable(JSON),
        default=list
    )
    result_type = Column(String, nullable=True)

    scenario = relationship("ScenarioModel", back_populates="sessions")
    session_states = relationship("SessionSuspectStateModel", back_populates="session")
    chat_messages = relationship("NpcChatMessageModel", back_populates="session")
    evidence_usages = relationship("SessionEvidenceUsageModel", back_populates="session")

class SessionSuspectStateModel(Base):
    __tablename__ = "session_suspect_states"
    session_id = Column(Integer, ForeignKey("sessions.id"), primary_key=True)
    suspect_id = Column(Integer, ForeignKey("suspects.id"), primary_key=True)
    revealed_secret_ids = Column(MutableList.as_mutable(JSON), default=list)
    is_closed = Column(Boolean, default=False)
    progress = Column(Float, default=0.0)

    session = relationship("SessionModel", back_populates="session_states")
    suspect = relationship("SuspectModel", back_populates="session_states")

class NpcChatMessageModel(Base):
    __tablename__ = "npc_chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    suspect_id = Column(Integer, ForeignKey("suspects.id"), nullable=False)
    sender_type = Column(String, nullable=False)  # "player" or "npc"
    text = Column(String, nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidences.id"))
    timestamp = Column(DateTime, default=datetime.now)

    session = relationship("SessionModel", back_populates="chat_messages")
    suspect = relationship("SuspectModel", back_populates="chat_messages")
    evidence = relationship("EvidenceModel")

class SessionEvidenceUsageModel(Base):
    __tablename__ = "session_evidence_usages"
    session_id = Column(Integer, ForeignKey("sessions.id"), primary_key=True)
    suspect_id = Column(Integer, ForeignKey("suspects.id"), primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id"), primary_key=True)
    used_at = Column(DateTime, default=datetime.now)

    session = relationship("SessionModel", back_populates="evidence_usages")
    suspect = relationship("SuspectModel", back_populates="evidence_usages")
    evidence = relationship("EvidenceModel", back_populates="evidence_usages")
```

---

## Arquivo: `app/main.py`

```python
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.sessions import router as sessions_router
from app.api.scenarios import router as scenarios_router
from app.services.bootstrap_service import bootstrap_game

app = FastAPI(title="Detective AI Game")

# -----------------------------
# Startup bootstrap (MVP)
# -----------------------------
@app.on_event("startup")
def startup_event():
    bootstrap_game()

# Register routes
app.include_router(sessions_router)
app.include_router(scenarios_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Arquivo: `app/services/__init__.py`

```python
# Services package
"""
Service layer contract (MVP):

- Services used by API controllers MUST return only
  serializable data structures (dict, list, str, int, etc).
- SQLAlchemy ORM objects must NEVER leak outside the service layer.
- Controllers should not depend on ORM behavior or session lifecycle.

This avoids DetachedInstanceError and keeps the API boundary stable.
"""
```

---

## Arquivo: `app/services/ai_adapter.py`

```python
"""
IA Adapter Interface for NPC Dialogue Generation.

This module defines the base interface used by the game to generate NPC
responses during interrogations. Real implementations (OpenAI, local LLM,
Claude, etc.) should inherit from `NpcAIAdapter` and override `generate_reply`.

No actual AI calls are performed in this interface.
"""

from typing import List, Dict, Any


class NpcAIAdapter:
    """
    Base interface for NPC dialogue generation.

    Any concrete implementation must override `generate_reply` and return
    a string representing the NPC's answer.

    Parameters expected:

    - suspect_state: dict with fields like:
        {
            "suspect_id": 1,
            "name": "Marina",
            "is_closed": False,
            "revealed_secrets": [
                {"secret_id": 1, "content": "...", "is_core": True},
            ],
            "personality": "cold and calculating",
            "final_phrase": "Já falei tudo que sabia."
        }

    - chat_history: list of messages (ordered), each being:
        {
            "sender": "player" | "npc",
            "text": "...",
            "evidence_id": 3 | None,
            "timestamp": "..."
        }

    - player_message: the last message sent by the player:
        {
            "text": "Explique isso",
            "evidence_id": 3 | None
        }

    Returns:
        str: the textual reply of the NPC.
    """

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        npc_context: Dict[str, Any] | None = None
    ) -> str:
        """
        npc_context:
            Contexto completo do NPC e do caso, preparado pelo backend.
            Pode conter cenário, verdades, mentiras, segredos revelados e regras.
        """
```

---

## Arquivo: `app/services/ai_adapter_dummy.py`

```python
"""
Dummy implementation of NpcAIAdapter.

This adapter does NOT use any real AI model.
It produces deterministic responses based on:
- revealed secrets
- hidden secrets
- personality
- evidence usage
- whether the suspect is 'closed'

Useful for testing the entire interrogation flow before integrating a real LLM.
"""

from typing import Dict, Any, List
from app.services.ai_adapter import NpcAIAdapter


class DummyNpcAIAdapter(NpcAIAdapter):
    """Deterministic, rule-based NPC reply generator."""

    def generate_reply(
        self,
        suspect_state: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        player_message: Dict[str, Any],
        npc_context: Dict[str, Any] | None = None
    ) -> str:

        name = suspect_state.get("name", "O suspeito")
        personality = suspect_state.get("personality", "neutro")
        is_closed = suspect_state.get("is_closed", False)
        final_phrase = suspect_state.get("final_phrase", "Já falei tudo que sabia.")
        revealed_secrets = suspect_state.get("revealed_secrets", [])
        hidden_secrets = suspect_state.get("hidden_secrets", [])
        evidence_id = player_message.get("evidence_id")

        # ----------------------------------------------------------------------
        # 1. Se o suspeito está "fechado", só devolve a frase final.
        # ----------------------------------------------------------------------
        if is_closed:
            return final_phrase

        # ----------------------------------------------------------------------
        # 2. Se o jogador usou uma evidência, reagimos a isso.
        # ----------------------------------------------------------------------
        if evidence_id is not None:
            # Se essa evidência revelou algum segredo recém descoberto...
            if revealed_secrets:
                revealed_texts = [s["content"] for s in revealed_secrets]
                combined = " ".join(revealed_texts)
                return (
                    f"...Tá bom, tá bom! Essa evidência me incrimina. "
                    f"{combined}"
                )
            else:
                return (
                    f"Isso? {name} olha para a evidência e dá de ombros. "
                    "“Isso não prova nada. Você está exagerando.”"
                )

        # ----------------------------------------------------------------------
        # 3. Se a pergunta não tem evidência, retornar algo genérico.
        # ----------------------------------------------------------------------

        if personality == "agressivo":
            return (
                f"{name} cruza os braços. “Por que eu perderia meu tempo respondendo isso? "
                "Fale algo que faça sentido.”"
            )
        elif personality == "nervoso":
            return (
                f"{name} engole seco. “E-eu já disse tudo o que sei. "
                "Vocês estão me assustando.”"
            )
        elif personality == "arrogante":
            return (
                f"{name} sorri com desprezo. “Vocês detetives são todos iguais. "
                "Perguntam demais e entendem de menos.”"
            )

        # Personalidade neutra / fallback
        return (
            f"{name} responde calmamente: "
            "“Olha, estou cooperando. Mas você precisa ser mais específico.”"
        )
```

---

## Arquivo: `app/services/ai_adapter_factory.py`

```python
import os

from app.services.ai_adapter_dummy import DummyNpcAIAdapter
from app.services.ai_adapter_openai import OpenAINpcAIAdapter


def get_npc_ai_adapter():
    provider = os.getenv("NPC_AI_PROVIDER", "dummy").lower()
    print(f"[AI] NPC_AI_PROVIDER = {provider}")

    if provider == "openai":
        print("[AI] Using OpenAI adapter")
        return OpenAINpcAIAdapter()

    print("[AI] Using Dummy adapter")
    return DummyNpcAIAdapter()
```

---

## Arquivo: `app/services/ai_adapter_openai.py`

```python
import os
from typing import Dict, Any, List

from openai import OpenAI
from app.services.ai_adapter import NpcAIAdapter
from app.services.prompt_builder import build_npc_prompt


class OpenAINpcAIAdapter(NpcAIAdapter):
    """
    Real AI adapter using OpenAI Responses API.

    IMPORTANT:
    - This adapter receives ONLY already-allowed information
    - It must never infer or invent secrets
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    def generate_reply(
        self,
        suspect_state: dict,
        chat_history: list,
        player_message: dict,
        npc_context: dict | None = None
    ) -> str:
        if not npc_context:
            raise ValueError("npc_context is required for OpenAI adapter")

        prompt = build_npc_prompt(
            npc_context=npc_context,
            chat_history=chat_history,
            player_message=player_message
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        return response.output_text.strip()
```

---

## Arquivo: `app/services/bootstrap_service.py`

```python
from pathlib import Path
from sqlalchemy.orm import Session

from app.infra.db import init_db, SessionLocal
from app.infra.db_models import ScenarioModel
from app.services.scenario_loader import load_scenario_from_json


SCENARIOS_DIR = Path("scenarios")


def bootstrap_game():
    """
    Bootstraps the game environment on API startup.

    Responsibilities:
    - Initialize database tables
    - Load scenario JSON files if no scenario exists
    - Ensure idempotency (safe to run multiple times)
    """

    # 1. Ensure DB schema exists
    init_db()

    db: Session = SessionLocal()
    try:
        # 2. Check if any scenario already exists
        existing = db.query(ScenarioModel).first()
        if existing:
            print("[bootstrap] Scenario(s) already present. Skipping load.")
            return

        # 3. Load all scenario JSON files
        if not SCENARIOS_DIR.exists():
            print("[bootstrap] No scenarios directory found. Skipping.")
            return

        json_files = list(SCENARIOS_DIR.glob("*.json"))

        if not json_files:
            print("[bootstrap] No scenario JSON files found. Skipping.")
            return

        print(f"[bootstrap] Loading {len(json_files)} scenario(s)...")

        for path in json_files:
            load_scenario_from_json(str(path), db=db)

        print("[bootstrap] Scenario bootstrap completed.")

    finally:
        db.close()
```

---

## Arquivo: `app/services/chat_service.py`

```python
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    SuspectModel,
    NpcChatMessageModel,
    SessionSuspectStateModel,
    SessionEvidenceUsageModel,
    SecretModel,
    EvidenceModel,
    ScenarioModel
)

from app.services.ai_adapter_factory import get_npc_ai_adapter
from app.services.npc_context_builder import build_npc_context

ai = get_npc_ai_adapter()

def add_player_message(
    session_id: int,
    suspect_id: int,
    text: str,
    evidence_id: Optional[int] = None,
    db: Optional[Session] = None
) -> dict:
    """
    Registers a player message and returns a clean dictionary with message info.
    Prevents DetachedInstanceError by not returning ORM objects.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Validate session
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        # Validate suspect
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id,
            SuspectModel.scenario_id == session.scenario_id
        ).first()
        if not suspect:
            raise ValueError(f"Suspect {suspect_id} is not part of scenario {session.scenario_id}.")

        # Validate evidence
        if evidence_id is not None:
            evidence = db.query(EvidenceModel).filter(
                EvidenceModel.id == evidence_id,
                EvidenceModel.scenario_id == session.scenario_id
            ).first()

            if not evidence:
                raise ValueError(
                    f"Evidence {evidence_id} is not valid for scenario {session.scenario_id}."
                )

        # Create message
        msg = NpcChatMessageModel(
            session_id=session_id,
            suspect_id=suspect_id,
            sender_type="player",
            text=text,
            evidence_id=evidence_id
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Log evidence usage

        if evidence_id is not None:
            existing = db.query(SessionEvidenceUsageModel).filter(
                SessionEvidenceUsageModel.session_id == session_id,
                SessionEvidenceUsageModel.suspect_id == suspect_id,
                SessionEvidenceUsageModel.evidence_id == evidence_id
            ).first()

            if not existing:
                usage = SessionEvidenceUsageModel(
                    session_id=session_id,
                    suspect_id=suspect_id,
                    evidence_id=evidence_id
                )
                db.add(usage)
                db.commit()


        # Convert ORM → dict before closing session
        result = {
            "id": msg.id,
            "session_id": msg.session_id,
            "suspect_id": msg.suspect_id,
            "text": msg.text,
            "sender_type": msg.sender_type,
            "evidence_id": msg.evidence_id,
            "timestamp": msg.timestamp.isoformat(),
        }

        return result

    finally:
        if close_session:
            db.close()

def add_npc_reply(
    session_id: int,
    suspect_id: int,
    player_message_id: int,
    db: Optional[Session] = None
) -> NpcChatMessageModel:
    """
    Generates an NPC reply after a player sends a message.

    Steps:
    1. Load suspect state (revealed secrets, closed flag, personality info)
    2. Load recent chat history
    3. Load the player message content
    4. Call the AI adapter to generate reply text
    5. Save NPC message to DB
    6. Return that DB object
    """

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # ----------------------------------------
        # 1. Load suspect state for this session
        # ----------------------------------------
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(f"Suspect {suspect_id} not part of session {session_id}.")

        # Load suspect model (for personality, final phrase, etc.)
        suspect = db.query(SuspectModel).filter(
            SuspectModel.id == suspect_id
        ).first()

        # ----------------------------------------
        # 2. Load chat history for this suspect/session
        # ----------------------------------------
        history_rows = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.session_id == session_id,
            NpcChatMessageModel.suspect_id == suspect_id
        ).order_by(NpcChatMessageModel.timestamp.asc()).all()

        chat_history = [
            {
                "sender": row.sender_type,
                "text": row.text,
                "evidence_id": row.evidence_id,
                "timestamp": row.timestamp.isoformat()
            }
            for row in history_rows
        ]

        # ----------------------------------------
        # 3. Load the player message
        # ----------------------------------------
        player_msg = db.query(NpcChatMessageModel).filter(
            NpcChatMessageModel.id == player_message_id
        ).first()

        if not player_msg:
            raise ValueError(f"Player message {player_message_id} not found.")

        player_message_dict = {
            "text": player_msg.text,
            "evidence_id": player_msg.evidence_id
        }

        # ----------------------------------------
        # 4. Build suspect_state for AI
        # ----------------------------------------
        revealed_secrets = []
        if state.revealed_secret_ids:
            secrets = db.query(SecretModel).filter(
                SecretModel.id.in_(state.revealed_secret_ids)
            ).all()
            for sc in secrets:
                revealed_secrets.append({
                    "secret_id": sc.id,
                    "content": sc.content,
                    "is_core": sc.is_core
                })

        # Hidden secrets (just for dummy AI)
        hidden_secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id
        ).all()

        hidden_list = [
            {"secret_id": sc.id, "content": sc.content, "is_core": sc.is_core}
            for sc in hidden_secrets
            if sc.id not in state.revealed_secret_ids
        ]

        suspect_state = {
            "suspect_id": suspect_id,
            "name": suspect.name if suspect else "O suspeito",
            "personality": suspect.backstory or "neutro",
            "revealed_secrets": revealed_secrets,
            "hidden_secrets": hidden_list,
            "is_closed": state.is_closed,
            "final_phrase": (
                suspect.final_phrase
                if suspect and suspect.final_phrase
                else "Já falei tudo que sabia."
            )
        }

        # ----------------------------------------
        # Load scenario
        # ----------------------------------------

        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == session_id)
            .first()
        )

        if not session:
            raise ValueError(f"Session {session_id} not found")        

        scenario = (
            db.query(ScenarioModel)
            .filter(ScenarioModel.id == session.scenario_id)
            .first()
        )

        if not scenario:
            raise ValueError("Scenario not found for session")

        # ----------------------------------------
        # Build pressure points (MVP)
        # ----------------------------------------
        pressure_points = [
            {
                "evidence_id": msg["evidence_id"],
                "text": msg["text"]
            }
            for msg in chat_history
            if msg.get("evidence_id") is not None
        ]

        # ----------------------------------------
        # Call AI adapter
        # ----------------------------------------
        npc_context = build_npc_context(
            scenario=scenario,
            suspect=suspect,
            suspect_state=suspect_state,
            revealed_secrets=revealed_secrets,
            pressure_points=pressure_points
        )

        reply_text = ai.generate_reply(
            suspect_state=suspect_state,
            npc_context=npc_context,
            chat_history=chat_history,
            player_message=player_message_dict
        )

        # ----------------------------------------
        # 6. Save NPC message
        # ----------------------------------------
        npc_msg = NpcChatMessageModel(
            session_id=session_id,
            suspect_id=suspect_id,
            sender_type="npc",
            text=reply_text
        )

        db.add(npc_msg)
        db.commit()
        db.refresh(npc_msg)

        return {
            "id": npc_msg.id,
            "session_id": npc_msg.session_id,
            "suspect_id": npc_msg.suspect_id,
            "sender_type": npc_msg.sender_type,
            "text": npc_msg.text,
            "evidence_id": npc_msg.evidence_id,
            "timestamp": npc_msg.timestamp.isoformat()
        }

    finally:
        if close_db:
            db.close()
```

---

## Arquivo: `app/services/npc_context_builder.py`

```python
def build_npc_context(
    scenario,
    suspect,
    suspect_state: dict,
    revealed_secrets: list,
    pressure_points: list,
    true_timeline: list | str,
    lies: list | str
) -> dict:
    return {
        "case": {
            "title": scenario.title,
            "description": scenario.description,
        },
        "suspect": {
            "id": suspect.id,
            "name": suspect.name,
            "backstory": suspect.backstory,
            "final_phrase": suspect.final_phrase,
            "is_closed": suspect_state.get("is_closed", False),
            "progress": suspect_state.get("progress", 0.0),
        },
        # 🔴 APENAS PARA IA
        "true_timeline": true_timeline,
        "lies": lies,
        # 🔴 CONTROLADO PELO BACKEND
        "revealed_secrets": revealed_secrets,
        "pressure_points": pressure_points,
        "rules": {
            "can_only_use_revealed_secrets": True,
            "never_invent_facts": True,
            "never_reveal_unmarked_information": True,
        }
    }
```

---

## Arquivo: `app/services/prompt_builder.py`

```python
def build_npc_prompt(
    npc_context,
    chat_history,
    player_message
):
    system_prompt = f"""
Você é um personagem suspeito em um jogo de investigação.

== NOME DO PERSONAGEM == 
{npc_context["suspect"]["name"]}

== CONTEXTO DO PERSONAGEM ==
{npc_context["suspect"]["backstory"]}

=== CONTEXTO DO CASO ===
{npc_context["case"]["description"]}

=== SUA HISTÓRIA REAL (NÃO É PÚBLICA) ===
{npc_context["true_timeline"]}

=== MENTIRAS QUE VOCÊ JÁ CONTOU ===
{npc_context["lies"]}

=== SEGREDOS JÁ REVELADOS AO JOGADOR ===
{npc_context["revealed_secrets"]}

=== REGRAS ABSOLUTAS ===
- Você sabe toda a verdade, mas NÃO pode revelá-la livremente.
- Você só pode afirmar fatos listados em "SEGREDOS JÁ REVELADOS".
- Se confrontado com evidências que quebram uma mentira:
  - demonstre tensão, evasão ou admissão parcial.
- Nunca revele o culpado final.
- Nunca invente fatos novos.
- Se estiver encerrado, responda apenas com sua frase final.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-10:]:
        role = "assistant" if msg["sender"] == "npc" else "user"
        messages.append({"role": role, "content": msg["text"]})

    messages.append({"role": "user", "content": player_message["text"]})

    return messages
```

---

## Arquivo: `app/services/scenario_loader.py`

```python
import json
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.schema_scenario import ScenarioConfig
from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SuspectModel,
    EvidenceModel,
    SecretModel
)


def load_scenario_from_json(path: str, db: Optional[Session] = None) -> ScenarioModel:
    """
    Loads a scenario from a JSON file, validates it via Pydantic,
    and populates the SQLAlchemy database models.
    Prevents duplication by checking scenario title.
    
    Args:
        path (str): Path to the scenario JSON file.
        db (Session, optional): Existing DB session (useful for tests).
    
    Returns:
        ScenarioModel: The scenario model saved in the database.
    """
    close_session = False

    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Load JSON
        # -------------------------
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # -------------------------
        # 2. Validate with Pydantic
        # -------------------------
        config = ScenarioConfig(**data)

        # -------------------------
        # 3. Check for duplicates
        # -------------------------
        existing = (
            db.query(ScenarioModel)
            .filter(ScenarioModel.title == config.title)
            .first()
        )

        if existing:
            print(f"[loader] Scenario '{config.title}' already exists. Skipping insert.")
            return existing

        # -------------------------
        # 4. Create Scenario
        # -------------------------
        scenario = ScenarioModel(
            title=config.title,
            description=config.description
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)

        # Maps for later linking secrets
        suspect_map = {}
        evidence_map = {}

        # -------------------------
        # 5. Insert Suspects
        # -------------------------
        for s in config.suspects:
            suspect = SuspectModel(
                scenario_id=scenario.id,
                name=s.name,
                backstory=s.backstory,
                initial_statement=s.initial_statement,
                final_phrase=s.final_phrase
            )
            db.add(suspect)
            db.commit()
            db.refresh(suspect)

            suspect_map[s.name] = suspect.id

        # -------------------------
        # 6. Insert Evidence
        # -------------------------
        mandatory_evidence_ids = []

        for e in config.evidences:
            evidence = EvidenceModel(
                scenario_id=scenario.id,
                name=e.name,
                description=e.description
            )
            db.add(evidence)
            db.commit()
            db.refresh(evidence)

            evidence_map[e.name] = evidence.id

            if e.is_mandatory:
                mandatory_evidence_ids.append(evidence.id)

        # -------------------------
        # 6.5 Persist verdict rules (T24.5)
        # -------------------------
        scenario.required_evidence_ids = mandatory_evidence_ids
        db.commit()
        db.refresh(scenario)

        # store mandatory evidence IDs inside scenario? (future)
        # for now we keep culprit only

        # -------------------------
        # 7. Set culprit
        # -------------------------
        if config.culprit not in suspect_map:
            raise ValueError(
                f"Culprit '{config.culprit}' not found among suspects."
            )

        scenario.culprit_id = suspect_map[config.culprit]
        db.commit()
        db.refresh(scenario)

        # -------------------------
        # 8. Insert Secrets
        # -------------------------
        for sec in config.secrets:
            if sec.suspect not in suspect_map:
                raise ValueError(
                    f"Secret references unknown suspect '{sec.suspect}'"
                )

            if sec.evidence not in evidence_map:
                raise ValueError(
                    f"Secret references unknown evidence '{sec.evidence}'"
                )

            secret = SecretModel(
                suspect_id=suspect_map[sec.suspect],
                evidence_id=evidence_map[sec.evidence],
                content=sec.content,
                is_core=sec.is_core
            )
            db.add(secret)

        db.commit()

        print(f"[loader] Scenario '{scenario.title}' loaded successfully.")
        return scenario

    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `app/services/secret_service.py`

```python
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SecretModel,
    SessionSuspectStateModel,
    SuspectModel
)


def apply_evidence_to_suspect(
    session_id: int,
    suspect_id: int,
    evidence_id: int,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Applies evidence to a suspect:
      - Reveals secrets associated with that evidence
      - Updates progress
      - If all core secrets are revealed, marks suspect as 'closed'
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ---------------------------------------
        # 1. Fetch state of suspect in this session
        # ---------------------------------------
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(f"Suspect {suspect_id} not part of session {session_id}.")

        # ---------------------------------------
        # 2. Find secrets revealed by this evidence
        # ---------------------------------------
        secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.evidence_id == evidence_id
        ).all()

        if not secrets:
            return []

        revealed_now = []

        # ---------------------------------------
        # 3. Reveal secrets (append only new ones)
        # ---------------------------------------
        for secret in secrets:
            if secret.id not in state.revealed_secret_ids:
                state.revealed_secret_ids.append(secret.id)
                revealed_now.append({
                    "secret_id": secret.id,
                    "content": secret.content,
                    "is_core": secret.is_core
                })

        # ---------------------------------------
        # 4. Recalculate progress (core secrets only)
        # ---------------------------------------
        all_core = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.is_core == True
        ).all()

        total_core = len(all_core)

        if total_core > 0:
            revealed_core = sum(
                1 for s in all_core if s.id in state.revealed_secret_ids
            )
            state.progress = revealed_core / total_core
        else:
            # No core secrets → progress always 1.0
            state.progress = 1.0

        # ---------------------------------------
        # 5. If all core secrets revealed → close suspect
        # ---------------------------------------
        if total_core > 0 and state.progress == 1.0:
            state.is_closed = True

        db.commit()
        db.refresh(state)

        return revealed_now

    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `app/services/session_finalize_service.py`

```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import SessionModel
from app.services.verdict_service import evaluate_verdict


def finalize_session(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Finalizes a game session:
    - Evaluates the verdict
    - Persists the result in the session
    - Marks the session as finished

    Returns:
        Dict with session_id, result_type and verdict details
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ----------------------------------------
        # 1. Load session
        # ----------------------------------------
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found.")

        if session.status == "finished":
            raise ValueError(f"Session {session_id} is already finished.")

        # ----------------------------------------
        # 2. Evaluate verdict
        # ----------------------------------------
        verdict = evaluate_verdict(
            session_id=session_id,
            chosen_suspect_id=chosen_suspect_id,
            evidence_ids=evidence_ids,
            db=db
        )

        # ----------------------------------------
        # 3. Persist result in session
        # ----------------------------------------
        session.chosen_suspect_id = chosen_suspect_id
        session.chosen_evidence_ids = evidence_ids or []
        session.result_type = verdict["result_type"]
        session.status = "finished"

        db.commit()
        db.refresh(session)

        # ----------------------------------------
        # 4. Return minimal useful data
        # ----------------------------------------
        return {
            "session_id": session.id,
            "status": session.status,
            "result_type": session.result_type,
            "verdict": verdict
        }

    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `app/services/session_service.py`

```python
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    ScenarioModel,
    SessionModel,
    SessionSuspectStateModel,
    SuspectModel,
    SecretModel
)


def create_session(scenario_id: int, db: Optional[Session] = None) -> SessionModel:
    """
    Creates a new game session for a given scenario.
    Initializes SessionModel + SessionSuspectState entries for each suspect.

    Args:
        scenario_id (int): ID of the scenario.
        db (Session, optional): Existing SQLAlchemy session.

    Returns:
        SessionModel: The newly created session with suspect states.
    """
    close_session = False

    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Validate scenario exists
        # -------------------------
        scenario = db.query(ScenarioModel).filter(ScenarioModel.id == scenario_id).first()

        if not scenario:
            raise ValueError(f"Scenario with id {scenario_id} does not exist.")

        # -------------------------
        # 2. Create session
        # -------------------------
        session = SessionModel(
            scenario_id=scenario_id,
            status="in_progress"
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # -------------------------
        # 3. Create initial suspect states
        # -------------------------
        suspects = db.query(SuspectModel).filter(SuspectModel.scenario_id == scenario_id).all()

        for suspect in suspects:
            state = SessionSuspectStateModel(
                session_id=session.id,
                suspect_id=suspect.id,
                revealed_secret_ids=[],
                is_closed=False,
                progress=0.0
            )
            db.add(state)

        db.commit()

        # Refresh session to load states
        db.refresh(session)

        result = {
            "id": session.id,
            "scenario_id": session.scenario_id,
            "status": session.status,
            "created_at": session.created_at.isoformat()
        }

        print(f"[session] Session {session.id} created for scenario {scenario_id}")
        return result

    finally:
        if close_session:
            db.close()

def get_session_overview(session_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Returns a structured overview of the session:
      - session info
      - scenario summary
      - list of suspects with progress (placeholder logic)
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # -------------------------
        # 1. Load session
        # -------------------------
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

        if not session:
            raise ValueError(f"Session with id {session_id} not found.")

        # -------------------------
        # 2. Load scenario
        # -------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        # -------------------------
        # 3. Load suspects + their session state
        # -------------------------
        suspects = (
            db.query(SuspectModel)
            .filter(SuspectModel.scenario_id == scenario.id)
            .all()
        )

        suspect_states = (
            db.query(SessionSuspectStateModel)
            .filter(SessionSuspectStateModel.session_id == session.id)
            .all()
        )

        # Map suspect_id → state
        state_map = {s.suspect_id: s for s in suspect_states}

        # -------------------------
        # 4. Assemble suspect summaries
        # -------------------------
        suspects_summary = []
        for s in suspects:
            s_state = state_map.get(s.id)

            progress = s_state.progress if s_state else 0.0

            # Pegar o status de 'fechado' (is_closed)
            is_closed = s_state.is_closed if s_state else False

            suspects_summary.append({
                "suspect_id": s.id,
                "name": s.name,
                "progress": progress,
                "is_closed": is_closed
            })

        # -------------------------
        # 5. Assemble final overview
        # -------------------------
        overview = {
            "session": {
                "id": session.id,
                "scenario_id": session.scenario_id,
                "status": session.status,
                "created_at": session.created_at.isoformat()
            },
            "scenario": {
                "title": scenario.title,
                "description": scenario.description,
                "objective": "find_culprit"  # placeholder objective for MVP
            },
            "suspects": suspects_summary
        }

        return overview

    finally:
        if close_session:
            db.close()

def calculate_suspect_progress(
    session_id: int,
    suspect_id: int,
    db: Optional[Session] = None
) -> float:
    """
    READ-ONLY helper.
    Calculates progress based on already persisted revealed secrets.
    Does NOT mutate database state.
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(
                f"Suspect {suspect_id} does not belong to session {session_id}."
            )

        core_secrets = db.query(SecretModel).filter(
            SecretModel.suspect_id == suspect_id,
            SecretModel.is_core == True
        ).all()

        total_core = len(core_secrets)
        if total_core == 0:
            return 1.0

        revealed_core = sum(
            1 for s in core_secrets if s.id in state.revealed_secret_ids
        )

        return revealed_core / total_core

    finally:
        if close_session:
            db.close()


def get_suspect_state(session_id: int, suspect_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Fetches the progress and closed status of a suspect in a given session.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Fetch the suspect's state for the given session
        state = db.query(SessionSuspectStateModel).filter(
            SessionSuspectStateModel.session_id == session_id,
            SessionSuspectStateModel.suspect_id == suspect_id
        ).first()

        if not state:
            raise ValueError(f"Suspect {suspect_id} not part of session {session_id}.")

        return {
            "progress": state.progress,
            "is_closed": state.is_closed
        }
    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `app/services/verdict_rules_service.py`

```python
from typing import List
from sqlalchemy.orm import Session
from app.infra.db_models import ScenarioModel
from app.infra.db import SessionLocal


def get_required_evidences_for_scenario(
    scenario_id: int,
    db: Session | None = None
) -> List[int]:
    """
    Returns the list of mandatory evidence IDs for a scenario.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == scenario_id
        ).first()

        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found.")

        return scenario.required_evidence_ids or []

    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `app/services/verdict_service.py`

```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infra.db import SessionLocal
from app.infra.db_models import (
    SessionModel,
    ScenarioModel
)


def evaluate_verdict(
    session_id: int,
    chosen_suspect_id: int,
    evidence_ids: List[int],
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Evaluates the final verdict of a session.

    Rules:
    - If chosen suspect is NOT the real culprit → result_type = "wrong"
    - If chosen suspect IS the real culprit:
        - If all required evidences are present → "correct"
        - Else → "partial"

    Returns:
        Dict with:
            - result_type
            - missing_evidence_ids
            - required_evidence_ids
            - chosen_suspect_id
            - real_culprit_id
    """

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # ----------------------------------------
        # 1. Load session
        # ----------------------------------------
        session = db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found.")

        # ----------------------------------------
        # 2. Load scenario
        # ----------------------------------------
        scenario = db.query(ScenarioModel).filter(
            ScenarioModel.id == session.scenario_id
        ).first()

        if not scenario:
            raise ValueError(
                f"Scenario {session.scenario_id} not found for session {session_id}."
            )

        real_culprit_id = scenario.culprit_id
        required_evidence_ids = scenario.required_evidence_ids or []

        # ----------------------------------------
        # 3. Wrong culprit → immediate fail
        # ----------------------------------------
        if chosen_suspect_id != real_culprit_id:
            return {
                "result_type": "wrong",
                "missing_evidence_ids": required_evidence_ids,
                "required_evidence_ids": required_evidence_ids,
                "chosen_suspect_id": chosen_suspect_id,
                "real_culprit_id": real_culprit_id,
            }

        # ----------------------------------------
        # 4. Culprit correct → check evidences
        # ----------------------------------------
        provided = set(evidence_ids or [])
        required = set(required_evidence_ids)

        missing = list(required - provided)

        if not missing:
            result_type = "correct"
        else:
            result_type = "partial"

        return {
            "result_type": result_type,
            "missing_evidence_ids": missing,
            "required_evidence_ids": required_evidence_ids,
            "chosen_suspect_id": chosen_suspect_id,
            "real_culprit_id": real_culprit_id,
        }

    finally:
        if close_session:
            db.close()
```

---

## Arquivo: `init_db.py`

```python
from app.infra.db import init_db

if __name__ == "__main__":
    init_db()
```

---

## Arquivo: `list_tables.py`

```python
import sqlite3

conn = sqlite3.connect("game.db")

cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables = cursor.fetchall()

print([table[0] for table in tables])

conn.close()
```

---

## Arquivo: `load.py`

```python
from app.services.scenario_loader import load_scenario_from_json

scenario = load_scenario_from_json("scenarios/piloto.json")
print("Loaded:", scenario.id, scenario.title)
```

---

