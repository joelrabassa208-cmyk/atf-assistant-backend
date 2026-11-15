"""Copia todos los datos del atf_assistant.db (SQLite) a la base de DATABASE_URL.

Normalmente no hace falta: el backend lo hace solo al arrancar si Postgres
está vacío. Sirve para hacerlo a mano o para rehacerlo con --force.

    set DATABASE_URL=postgresql://...      (PowerShell: $env:DATABASE_URL="...")
    alembic upgrade head
    python scripts/sqlite_to_postgres.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR, DATABASE_URL  # noqa: E402
from app.db.database import session  # noqa: E402
from app.db.seed import copy_from_sqlite  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default=str(BASE_DIR / "atf_assistant.db"))
    parser.add_argument("--force", action="store_true", help="vaciar tablas destino antes de copiar")
    args = parser.parse_args()

    if DATABASE_URL.startswith("sqlite"):
        sys.exit("DATABASE_URL no está configurada: el destino sería el mismo SQLite.")

    with session() as db:
        counts = copy_from_sqlite(db, Path(args.sqlite), force=args.force)
    for table, count in counts.items():
        print(f"{table}: {count} filas")
    print("Listo.")


if __name__ == "__main__":
    main()
