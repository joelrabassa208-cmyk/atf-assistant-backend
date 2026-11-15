import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

from database import get_connection, create_database
from import_consolidated_data import import_data


load_dotenv()

VERSION = "1.6.0"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
logger = logging.getLogger("atf_assistant")


@asynccontextmanager
async def lifespan(_app):
    create_database()
    import_data()
    yield


app = FastAPI(
    title="ATF Assistant Backend",
    version=VERSION,
    lifespan=lifespan,
)

# CORS: lista separada por comas en ALLOWED_ORIGINS (ej. https://mi-front.onrender.com).
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key"],
    )


def _check_key(expected: str | None, provided: str | None):
    if expected and not (provided and secrets.compare_digest(provided, expected)):
        raise HTTPException(status_code=401, detail="Clave de acceso inválida")


def require_api_key(x_api_key: str | None = Header(default=None)):
    """Protege el asistente IA si ATF_API_KEY está configurada (opcional)."""
    _check_key(os.getenv("ATF_API_KEY"), x_api_key)


def require_admin_key(x_admin_key: str | None = Header(default=None)):
    """Las acciones de revisión exigen ATF_ADMIN_KEY; sin ella quedan deshabilitadas."""
    expected = os.getenv("ATF_ADMIN_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Revisión deshabilitada: falta ATF_ADMIN_KEY")
    _check_key(expected, x_admin_key)


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    catalog_id: int | None = None
    vehicle_id: int | None = None


class ReviewRequest(BaseModel):
    validation_status: Literal["WORKSHOP_CONFIRMED", "PENDING_REVIEW", "REJECTED"]
    reviewed_by: str = Field(min_length=1, max_length=100)
    review_notes: str | None = Field(default=None, max_length=1000)


CATALOG_SELECT = """
    SELECT
      tr.id, tr.brand, tr.model, tr.engine, tr.year_from,
      COALESCE(tr.year_to, tr.year_to_label) AS year_to,
      tr.transmission_type, tr.transmission_code,
      tr.reference_liters, tr.oem_specification,
      tr.suggested_product,
      wr.vehicle_description AS workshop_vehicle,
      wr.liters_used AS workshop_liters,
      wr.atf_used AS workshop_atf,
      wr.filter_1, wr.filter_2, wr.notes AS workshop_notes,
      wr.original_status AS workshop_status,
      cad.match_confidence, cad.review_reason,
      cad.validation_status,
      cad.reviewed_at, cad.reviewed_by, cad.review_notes
    FROM technical_reference_records tr
    JOIN consolidated_atf_data cad
      ON cad.technical_reference_id = tr.id
    LEFT JOIN workshop_records wr
      ON wr.id = cad.workshop_record_id
"""


@app.get("/")
def root():
    connection = get_connection()
    try:
        connection.execute("SELECT 1").fetchone()
        database = "connected"
    except Exception:
        database = "error"
    finally:
        connection.close()
    return {
        "status": "ok",
        "service": "ATF Assistant Backend",
        "version": VERSION,
        "database": database,
    }


@app.get("/api/vehicles")
def get_vehicles():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                v.id,
                b.name AS brand,
                m.name AS model,
                v.year_from,
                v.year_to,
                v.version,
                v.engine,
                v.fuel,
                v.drivetrain,
                t.manufacturer AS transmission_manufacturer,
                t.code AS transmission_code,
                t.type AS transmission_type,
                t.gears,
                vt.validation_status
            FROM vehicle_variants v
            JOIN models m
                ON m.id = v.model_id
            JOIN brands b
                ON b.id = m.brand_id
            LEFT JOIN vehicle_transmissions vt
                ON vt.vehicle_variant_id = v.id
            LEFT JOIN transmissions t
                ON t.id = vt.transmission_id
            ORDER BY
                b.name,
                m.name,
                v.year_from,
                v.version
            """
        ).fetchall()

        return {
            "status": "ok",
            "count": len(rows),
            "vehicles": [dict(row) for row in rows],
        }

    finally:
        connection.close()


@app.get("/api/atf-catalog")
def get_atf_catalog(
    brand: str | None = None,
    model: str | None = None,
    pending_only: bool = False,
):
    connection = get_connection()
    try:
        where = []
        params = []
        if brand:
            where.append("LOWER(tr.brand) = LOWER(?)")
            params.append(brand)
        if model:
            escaped = model.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where.append("LOWER(tr.model) LIKE LOWER(?) ESCAPE '\\'")
            params.append(f"%{escaped}%")
        if pending_only:
            where.append("cad.validation_status = 'PENDING_REVIEW'")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = connection.execute(
            f"""
            {CATALOG_SELECT}
            {clause}
            ORDER BY tr.brand, tr.model, tr.year_from, tr.engine
            """,
            params,
        ).fetchall()
        return {"status": "ok", "count": len(rows), "vehicles": [dict(row) for row in rows]}
    finally:
        connection.close()


@app.get("/api/atf-catalog/{record_id}")
def get_atf_catalog_record(record_id: int):
    connection = get_connection()
    try:
        row = connection.execute(
            CATALOG_SELECT + """
            WHERE tr.id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
        result = catalog_detail(row)
        return {"status": "ok", "vehicle": result}
    finally:
        connection.close()


SAFETY_NOTICES = {
    "PENDING_REVIEW": "Dato pendiente de revisión técnica. Confirmar código físico de caja y especificación OEM antes del servicio.",
    "REJECTED": "Registro descartado en revisión técnica. No usar como referencia.",
    "WORKSHOP_CONFIRMED": "Dato respaldado por experiencia registrada del taller. Confirmar nivel final según procedimiento técnico.",
}


def catalog_detail(row):
    result = dict(row)
    # `or` descartaba 0 litros como si fuera vacío; se compara contra None.
    workshop_liters = result.get("workshop_liters")
    result["recommended_service_liters"] = (
        workshop_liters if workshop_liters is not None else result.get("reference_liters")
    )
    result["service_liters_source"] = "WORKSHOP" if workshop_liters is not None else "REFERENCE"
    result["safety_notice"] = SAFETY_NOTICES.get(
        result.get("validation_status"), SAFETY_NOTICES["PENDING_REVIEW"]
    )
    return result


@app.patch("/api/atf-catalog/{record_id}/review", dependencies=[Depends(require_admin_key)])
def review_atf_catalog_record(record_id: int, review: ReviewRequest):
    """Revisión manual. Queda fija: la importación al arrancar ya no la pisa."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE consolidated_atf_data
            SET validation_status = ?, reviewed_by = ?, review_notes = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE technical_reference_id = ?
            """,
            (review.validation_status, review.reviewed_by, review.review_notes, record_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
        connection.commit()
        row = connection.execute(CATALOG_SELECT + " WHERE tr.id = ?", (record_id,)).fetchone()
        return {"status": "ok", "vehicle": catalog_detail(row)}
    finally:
        connection.close()


@app.get("/api/atf-stats")
def get_atf_stats():
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM workshop_records) AS workshop_records,
              (SELECT COUNT(*) FROM technical_reference_records) AS technical_references,
              SUM(CASE WHEN workshop_record_id IS NOT NULL THEN 1 ELSE 0 END) AS linked_references,
              SUM(CASE WHEN validation_status = 'PENDING_REVIEW' THEN 1 ELSE 0 END) AS pending_review,
              SUM(CASE WHEN validation_status = 'WORKSHOP_CONFIRMED' THEN 1 ELSE 0 END) AS workshop_confirmed,
              SUM(CASE WHEN validation_status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
              SUM(CASE WHEN reviewed_at IS NOT NULL THEN 1 ELSE 0 END) AS manually_reviewed
            FROM consolidated_atf_data
            """
        ).fetchone()
        return {"status": "ok", "stats": dict(row)}
    finally:
        connection.close()


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: int):
    connection = get_connection()
    try:
        result = vehicle_detail(connection, vehicle_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Vehículo no encontrado",
            )
        return {
            "status": "ok",
            "vehicle": result,
        }
    finally:
        connection.close()


def vehicle_detail(connection, vehicle_id):
    vehicle = connection.execute(
        """
        SELECT
            v.id,
            b.name AS brand,
            m.name AS model,
            v.market,
            v.year_from,
            v.year_to,
            v.version,
            v.engine,
            v.fuel,
            v.drivetrain,
            v.notes AS vehicle_notes,
            t.manufacturer AS transmission_manufacturer,
            t.code AS transmission_code,
            t.type AS transmission_type,
            t.gears,
            vt.id AS vehicle_transmission_id,
            vt.validation_status AS transmission_validation_status,
            vt.notes AS transmission_notes
        FROM vehicle_variants v
        JOIN models m
            ON m.id = v.model_id
        JOIN brands b
            ON b.id = m.brand_id
        LEFT JOIN vehicle_transmissions vt
            ON vt.vehicle_variant_id = v.id
        LEFT JOIN transmissions t
            ON t.id = vt.transmission_id
        WHERE v.id = ?
        ORDER BY vt.id
        """,
        (vehicle_id,),
    ).fetchone()

    if vehicle is None:
        return None

    result = dict(vehicle)

    vehicle_transmission_id = result.get("vehicle_transmission_id")
    fluid_data = None

    if vehicle_transmission_id is not None:
        fluid = connection.execute(
            """
            SELECT
                f.manufacturer AS fluid_manufacturer,
                f.name AS fluid_name,
                COALESCE(tfd.specification, f.specification)
                    AS specification,
                tfd.total_capacity_l,
                tfd.service_capacity_l,
                tfd.level_check_method,
                tfd.validation_status,
                s.publisher AS source_publisher,
                s.title AS source_title,
                s.document_year AS source_year,
                s.url AS source_url,
                tfd.notes
            FROM transmission_fluid_data tfd
            LEFT JOIN fluids f
                ON f.id = tfd.fluid_id
            LEFT JOIN sources s
                ON s.id = tfd.source_id
            WHERE tfd.vehicle_transmission_id = ?
            ORDER BY tfd.id DESC
            LIMIT 1
            """,
            (vehicle_transmission_id,),
        ).fetchone()

        if fluid is not None:
            fluid_data = dict(fluid)

    result["fluid_data"] = fluid_data
    result["technical_data_status"] = (
        "AVAILABLE" if fluid_data is not None else "PENDING_REVIEW"
    )
    return result


def assistant_context(request: AssistantRequest):
    """Datos de la base para que la IA responda sobre el vehículo elegido."""
    if request.catalog_id is None and request.vehicle_id is None:
        return None
    connection = get_connection()
    try:
        parts = []
        if request.catalog_id is not None:
            row = connection.execute(
                CATALOG_SELECT + " WHERE tr.id = ?", (request.catalog_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
            parts.append(("Registro del catálogo ATF", catalog_detail(row)))
        if request.vehicle_id is not None:
            vehicle = vehicle_detail(connection, request.vehicle_id)
            if vehicle is None:
                raise HTTPException(status_code=404, detail="Vehículo no encontrado")
            parts.append(("Ficha de vehículo", vehicle))
    finally:
        connection.close()

    lines = []
    for title, data in parts:
        lines.append(f"## {title}")
        for key, value in data.items():
            if value not in (None, ""):
                lines.append(f"- {key}: {value}")
    return "\n".join(lines)


@app.post("/atf-assistant", dependencies=[Depends(require_api_key)])
def atf_assistant(request: AssistantRequest):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY no configurada",
        )

    context = assistant_context(request)
    user_input = request.message
    if context:
        user_input = (
            "Datos de la base ATF Assistant (respetá su validation_status; "
            "si dice PENDING_REVIEW o REJECTED, no los presentes como confirmados):\n"
            f"{context}\n\n## Consulta del técnico\n{request.message}"
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions="""
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
""",
            input=user_input,
        )

        return {
            "status": "ok",
            "response": response.output_text,
        }

    except Exception:
        # El detalle va al log del servidor, no al cliente (puede exponer datos internos).
        logger.exception("Error llamando a OpenAI")
        raise HTTPException(
            status_code=502,
            detail="El asistente IA no está disponible en este momento. Intentá de nuevo.",
        )
