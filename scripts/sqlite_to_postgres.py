"""Copia todos los datos del atf_assistant.db (SQLite) a la base de DATABASE_URL.

Uso (una sola vez, con la base Postgres ya migrada):

    set DATABASE_URL=postgresql://...      (PowerShell: $env:DATABASE_URL="...")
    alembic upgrade head
    python scripts/sqlite_to_postgres.py

Conserva los id originales y ajusta las secuencias de Postgres. Si una tabla
destino ya tiene filas, se omite (usar --force para vaciarlas antes).
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR, DATABASE_URL  # noqa: E402
from app.db.database import session  # noqa: E402

# Orden de dependencias (padres antes que hijos).
TABLES = [
    "brands", "models", "vehicle_variants", "transmissions", "sources",
    "vehicle_transmissions", "fluids", "transmission_fluid_data", "procedures",
    "procedure_steps", "vins", "workshop_records", "technical_reference_records",
    "consolidated_atf_data",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default=str(BASE_DIR / "atf_assistant.db"))
    parser.add_argument("--force", action="store_true", help="vaciar tablas destino antes de copiar")
    args = parser.parse_args()

    if DATABASE_URL.startswith("sqlite"):
        sys.exit("DATABASE_URL no está configurada: el destino sería el mismo SQLite.")

    source = sqlite3.connect(args.sqlite)
    source.row_factory = sqlite3.Row
    with session() as db:
        if args.force:
            for table in reversed(TABLES):
                db.execute(f"DELETE FROM {table}")
        for table in TABLES:
            if db.one(f"SELECT COUNT(*) AS n FROM {table}")["n"]:
                print(f"{table}: ya tiene datos, se omite")
                continue
            target_columns = {
                row["column_name"]
                for row in db.all(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = :t",
                    {"t": table},
                )
            }
            rows = [dict(row) for row in source.execute(f"SELECT * FROM {table}")]
            for row in rows:
                row = {key: value for key, value in row.items() if key in target_columns}
                columns = ", ".join(row)
                values = ", ".join(f":{key}" for key in row)
                db.execute(f"INSERT INTO {table} ({columns}) VALUES ({values})", row)
            db.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
            )
            print(f"{table}: {len(rows)} filas")
    print("Listo.")


if __name__ == "__main__":
    main()
