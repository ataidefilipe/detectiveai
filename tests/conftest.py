import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.infra.db_models import Base

import app.infra.db as db_module
import app.api.sessions as api_sessions
import app.services.chat_service as chat_service
import app.services.secret_service as secret_service
import app.services.session_service as session_service
import app.services.session_finalize_service as session_finalize_service
import app.services.verdict_service as verdict_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)

# Monkeypatching the global SessionLocal objects
db_module.engine = engine
db_module.SessionLocal = TestingSessionLocal
api_sessions.SessionLocal = TestingSessionLocal
chat_service.SessionLocal = TestingSessionLocal
secret_service.SessionLocal = TestingSessionLocal
session_service.SessionLocal = TestingSessionLocal
session_finalize_service.SessionLocal = TestingSessionLocal
verdict_service.SessionLocal = TestingSessionLocal

@pytest.fixture(autouse=True)
def truncate_tables():
    # To keep scenarios persistent between tests but clear sessions
    # Actually, simplest is to let drop_all run, because loading pilot scenario takes <50ms.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
