"""Run from the demo root: python -m backend.seed"""
from .repository import make_repository, seed_database

if __name__ == "__main__":
    repository = make_repository()
    if repository.dsn:
        raise SystemExit("Refusing to seed a PostgreSQL database. This command only creates the local SQLite fixture.")
    if repository.sqlite_path.exists():
        raise SystemExit(f"Already present; no changes: {repository.sqlite_path}")
    seed_database(repository.sqlite_path)
    print(f"Created local SQLite fixture: {repository.sqlite_path}")
