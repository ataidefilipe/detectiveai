"""
Reseta o banco SQLite de desenvolvimento.
Uso: python scripts/reset_dev_db.py

⚠️  DESTRÓI TODOS OS DADOS. Apenas para dev/teste.
"""
import os
import sys

# Adicionar root do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.db import engine, Base
from app.infra.db_models import *  # noqa: F403 — importa todos os models para registrá-los

from app.services.bootstrap_service import bootstrap_game

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./game.db").replace("sqlite:///", "")

def reset():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[OK] Removido: {DB_PATH}")
    else:
        print(f"[INFO] Banco não existia: {DB_PATH}")

    Base.metadata.create_all(bind=engine)
    print("[OK] Banco recriado com schema atualizado.")
    bootstrap_game()
    print("[OK] Cenários carregados via bootstrap.")

if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    if force:
        reset()
    else:
        confirm = input("Apagar banco e recriar? (y/N): ")
        if confirm.lower() == "y":
            reset()
        else:
            print("Cancelado.")
