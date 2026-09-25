import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from database import get_connection, create_database


load_dotenv()

app = FastAPI(
    title="ATF Assistant Backend",
    version="1.4.0",
)


class AssistantRequest(BaseModel):
    message: str


@app.on_event("startup")
def startup():
    create_database()


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ATF Assistant Backend",
        "version": "1.4.0",
        "database": "connected",
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


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: int):
    connection = get_connection()

    try:
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
            """,
            (vehicle_id,),
        ).fetchone()

        if vehicle is None:
            raise HTTPException(
                status_code=404,
                detail="Vehículo no encontrado",
            )

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

        return {
            "status": "ok",
            "vehicle": result,
        }

    finally:
        connection.close()


@app.post("/atf-assistant")
def atf_assistant(request: AssistantRequest):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY no configurada",
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
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
            input=request.message,
        )

        return {
            "status": "ok",
            "response": response.output_text,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error del asistente IA: {str(error)}",
        )
