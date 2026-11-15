"""Copia los datos del atf_assistant.db (SQLite del repo) a otra base.

Se usa sola al arrancar con Postgres vacío, y también desde
scripts/sqlite_to_postgres.py.
"""
import logging
import sqlite3
from pathlib import Path

from app.db.database import Database

logger = logging.getLogger("atf_assistant")

# Orden de dependencias (padres antes que hijos).
TABLES = [
    "brands", "models", "vehicle_variants", "transmissions", "sources",
    "vehicle_transmissions", "fluids", "transmission_fluid_data", "procedures",
    "procedure_steps", "vins", "workshop_records", "technical_reference_records",
    "consolidated_atf_data",
]


def is_empty(db: Database) -> bool:
    return not db.one("SELECT COUNT(*) AS n FROM brands")["n"]


def copy_from_sqlite(db: Database, sqlite_path: Path, force: bool = False) -> dict[str, int]:
    """Copia tabla por tabla conservando los id. Solo para Postgres."""
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    counts = {}
    try:
        if force:
            for table in reversed(TABLES):
                db.execute(f"DELETE FROM {table}")
        for table in TABLES:
            if db.one(f"SELECT COUNT(*) AS n FROM {table}")["n"]:
                logger.info("%s: ya tiene datos, se omite", table)
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
            counts[table] = len(rows)
    finally:
        source.close()
    return counts
