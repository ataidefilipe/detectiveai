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
    culprit_id = Column(Integer)  # Not FK, as it's a reference to Suspect

    suspects = relationship("SuspectModel", back_populates="scenario")
    evidences = relationship("EvidenceModel", back_populates="scenario")
    sessions = relationship("SessionModel", back_populates="scenario")

class SuspectModel(Base):
    __tablename__ = "suspects"
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    name = Column(String, nullable=False)
    backstory = Column(String)

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
