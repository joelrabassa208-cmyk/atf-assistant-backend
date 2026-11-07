"""Configuración leída de variables de entorno (una sola fuente de verdad)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv es opcional fuera de desarrollo
    pass
else:
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION = "2.0.0"

# Sin DATABASE_URL se usa el SQLite local del repo (desarrollo).
# En producción: postgresql+psycopg://usuario:clave@host:5432/base
_url = os.getenv("DATABASE_URL", "").strip()
if _url.startswith("postgres://"):
    # Render y Heroku entregan "postgres://"; SQLAlchemy 2 exige el driver explícito.
    _url = "postgresql+psycopg://" + _url[len("postgres://"):]
elif _url.startswith("postgresql://"):
    _url = "postgresql+psycopg://" + _url[len("postgresql://"):]
DATABASE_URL = _url or f"sqlite:///{BASE_DIR / 'atf_assistant.db'}"

# Importar las planillas de data/ al arrancar (comportamiento de la v1.x).
IMPORT_ON_STARTUP = os.getenv("IMPORT_ON_STARTUP", "true").lower() in {"1", "true", "yes"}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

ATF_API_KEY = os.getenv("ATF_API_KEY")
ATF_ADMIN_KEY = os.getenv("ATF_ADMIN_KEY")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
