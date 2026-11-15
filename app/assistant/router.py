import logging

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from app import config
from app.catalog import service
from app.db.database import Database, get_db
from app.security import require_api_key

router = APIRouter()
logger = logging.getLogger("atf_assistant")

INSTRUCTIONS = """
Sos ATF Assistant, un asistente técnico especializado en
servicios de transmisiones automáticas para talleres.

Tu función es asistir al técnico durante un procedimiento.

Reglas importantes:

- Respondé en español claro y profesional.
- Tené en cuenta el vehículo, motor, transmisión, VIN y etapa
  del procedimiento cuando esa información aparezca en la consulta.
- Priorizá siempre la seguridad.
- No inventes capacidades, cantidades de fluido, temperaturas,
  presiones, pares de apriete, especificaciones ATF ni procedimientos.
- Si un dato técnico no está validado o no fue proporcionado,
  indicá claramente que debe verificarse en documentación técnica
  validada antes de continuar.
- No presentes información estimada como si fuera un dato técnico
  confirmado.
- Ayudá al técnico a interpretar y comprender el procedimiento,
  pero no reemplaces documentación técnica validada.
- Respondé de forma concreta y útil para trabajar dentro del taller.
"""


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    catalog_id: int | None = None
    vehicle_id: int | None = None


def build_context(db: Database, request: AssistantRequest) -> str | None:
    """Datos de la base para que la IA responda sobre el vehículo elegido."""
    parts = []
    if request.catalog_id is not None:
        record = service.get_catalog_record(db, request.catalog_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
        parts.append(("Registro del catálogo ATF", record))
    if request.vehicle_id is not None:
        vehicle = service.get_vehicle(db, request.vehicle_id)
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        parts.append(("Ficha de vehículo", vehicle))
    if not parts:
        return None
    lines = []
    for title, data in parts:
        lines.append(f"## {title}")
        for key, value in data.items():
            if value not in (None, ""):
                lines.append(f"- {key}: {value}")
    return "\n".join(lines)


@router.post("/atf-assistant", dependencies=[Depends(require_api_key)])
def atf_assistant(request: AssistantRequest, db: Database = Depends(get_db)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurada")

    context = build_context(db, request)
    user_input = request.message
    if context:
        user_input = (
            "Datos de la base ATF Assistant (respetá su validation_status; "
            "si dice PENDING_REVIEW o REJECTED, no los presentes como confirmados):\n"
            f"{context}\n\n## Consulta del técnico\n{request.message}"
        )

    try:
        response = OpenAI(api_key=config.OPENAI_API_KEY).responses.create(
            model=config.OPENAI_MODEL,
            instructions=INSTRUCTIONS,
            input=user_input,
        )
    except Exception:
        # El detalle va al log del servidor, no al cliente.
        logger.exception("Error llamando a OpenAI")
        raise HTTPException(
            status_code=502,
            detail="El asistente IA no está disponible en este momento. Intentá de nuevo.",
        )
    return {"status": "ok", "response": response.output_text}
