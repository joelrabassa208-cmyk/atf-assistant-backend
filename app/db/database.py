"""Acceso a la base.

Las rutas reciben un objeto `Database` con tres métodos (`all`, `one`,
`execute`) y SQL con parámetros con nombre (`:id`). Así el mismo código corre
sobre SQLite (desarrollo) y Postgres (producción), y los tests pueden usar
sqlite3 sin depender de SQLAlchemy.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Protocol


class Database(Protocol):
    def all(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]: ...
    def one(self, sql: str, params: dict | None = None) -> dict[str, Any] | None: ...
    def execute(self, sql: str, params: dict | None = None) -> int: ...


class SqlAlchemyDatabase:
    def __init__(self, connection):
        self._connection = connection

    def all(self, sql, params=None):
        from sqlalchemy import text
        return [dict(row) for row in self._connection.execute(text(sql), params or {}).mappings()]

    def one(self, sql, params=None):
        from sqlalchemy import text
        row = self._connection.execute(text(sql), params or {}).mappings().first()
        return dict(row) if row is not None else None

    def execute(self, sql, params=None):
        from sqlalchemy import text
        return self._connection.execute(text(sql), params or {}).rowcount


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine, event

        from app.config import DATABASE_URL

        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        if _engine.dialect.name == "sqlite":
            @event.listens_for(_engine, "connect")
            def _sqlite_fk(dbapi_connection, _record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.close()
    return _engine


@contextmanager
def session() -> Iterator[Database]:
    """Una transacción: commit al salir sin errores, rollback si falla."""
    with get_engine().begin() as connection:
        yield SqlAlchemyDatabase(connection)


def get_db() -> Iterator[Database]:
    """Dependencia de FastAPI."""
    with session() as db:
        yield db
