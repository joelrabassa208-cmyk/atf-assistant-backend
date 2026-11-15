"""Claves de acceso. En la etapa 2 se reemplazan por usuarios con login (JWT)."""
import secrets

from fastapi import Header, HTTPException

from app import config


def _check_key(expected: str | None, provided: str | None):
    if expected and not (provided and secrets.compare_digest(provided, expected)):
        raise HTTPException(status_code=401, detail="Clave de acceso inválida")


def require_api_key(x_api_key: str | None = Header(default=None)):
    """Protege el asistente IA si ATF_API_KEY está configurada (opcional)."""
    _check_key(config.ATF_API_KEY, x_api_key)


def require_admin_key(x_admin_key: str | None = Header(default=None)):
    """Las acciones de revisión exigen ATF_ADMIN_KEY; sin ella quedan deshabilitadas."""
    if not config.ATF_ADMIN_KEY:
        raise HTTPException(status_code=503, detail="Revisión deshabilitada: falta ATF_ADMIN_KEY")
    _check_key(config.ATF_ADMIN_KEY, x_admin_key)
