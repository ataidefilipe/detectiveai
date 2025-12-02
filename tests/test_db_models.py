import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine
from app.infra.db_models import Base

engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

print("Tables created successfully.")
