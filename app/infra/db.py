import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .db_models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./game.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

SQLALCHEMY_DATABASE_URL = DATABASE_URL

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            table_names = inspector.get_table_names()

            if "sessions" in table_names:
                columns = [c["name"] for c in inspector.get_columns("sessions")]
                if "user_id" not in columns:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    conn.commit()

            if "suspects" in table_names:
                s_cols = [c["name"] for c in inspector.get_columns("suspects")]
                if "role_title" not in s_cols:
                    conn.execute(text("ALTER TABLE suspects ADD COLUMN role_title VARCHAR"))
                if "image_url" not in s_cols:
                    conn.execute(text("ALTER TABLE suspects ADD COLUMN image_url VARCHAR"))
                conn.commit()

            if "evidences" in table_names:
                e_cols = [c["name"] for c in inspector.get_columns("evidences")]
                if "image_url" not in e_cols:
                    conn.execute(text("ALTER TABLE evidences ADD COLUMN image_url VARCHAR"))
                conn.commit()
        except Exception:
            pass
