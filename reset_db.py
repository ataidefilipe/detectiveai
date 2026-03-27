import argparse
from app.infra.db_models import Base
from app.infra.db import engine

def reset_db(force: bool = False):
    if not force:
        print("WARNING: This will drop all tables and data in game.db!")
        confirm = input("Are you sure? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset the local SQLite game database.")
    parser.add_argument("--force", "-f", action="store_true", help="Force reset without confirmation prompt")
    args = parser.parse_args()
    
    reset_db(force=args.force)
