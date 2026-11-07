import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.assistant.router import router as assistant_router
from app.catalog.router import router as catalog_router
from app.db.database import session

logger = logging.getLogger("atf_assistant")


def run_migrations():
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(config.BASE_DIR / "alembic.ini")), "head")


@asynccontextmanager
async def lifespan(_app):
    # Con una sola instancia (plan actual de Render) es seguro migrar al arrancar.
    # Con varias instancias, poner RUN_MIGRATIONS=false y migrar en el deploy.
    if os.getenv("RUN_MIGRATIONS", "true").lower() in {"1", "true", "yes"}:
        run_migrations()
    if config.IMPORT_ON_STARTUP:
        from app.importers.consolidated import import_data

        with session() as db:
            counts = import_data(db)
        logger.info("Importación: %s", counts)
    yield


app = FastAPI(title="ATF Assistant Backend", version=config.VERSION, lifespan=lifespan)

if config.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key"],
    )


@app.get("/")
def root():
    try:
        with session() as db:
            db.one("SELECT 1 AS ok")
        database = "connected"
    except Exception:
        logger.exception("Base de datos no disponible")
        database = "error"
    return {
        "status": "ok",
        "service": "ATF Assistant Backend",
        "version": config.VERSION,
        "database": database,
    }


app.include_router(catalog_router)
app.include_router(assistant_router)
