import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from database import get_connection, create_database
from import_consolidated_data import import_data


load_dotenv()

app = FastAPI(
    title="ATF Assistant Backend",
    version="1.5.0",
)


class AssistantRequest(BaseModel):
    message: str


@app.on_event("startup")
def startup():
    create_database()
    import_data()


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ATF Assistant Backend",
        "version": "1.5.0",
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
            where.append("LOWER(tr.model) LIKE LOWER(?)")
            params.append(f"%{model}%")
        if pending_only:
            where.append("cad.validation_status = 'PENDING_REVIEW'")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = connection.execute(
            f"""
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
              cad.validation_status
            FROM technical_reference_records tr
            JOIN consolidated_atf_data cad
              ON cad.technical_reference_id = tr.id
            LEFT JOIN workshop_records wr
              ON wr.id = cad.workshop_record_id
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
            """
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
              cad.validation_status
            FROM technical_reference_records tr
            JOIN consolidated_atf_data cad
              ON cad.technical_reference_id = tr.id
            LEFT JOIN workshop_records wr
              ON wr.id = cad.workshop_record_id
            WHERE tr.id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
        result = dict(row)
        result["recommended_service_liters"] = result.get("workshop_liters") or result.get("reference_liters")
        result["service_liters_source"] = "WORKSHOP" if result.get("workshop_liters") is not None else "REFERENCE"
        result["safety_notice"] = (
            "Dato pendiente de revisión técnica. Confirmar código físico de caja y especificación OEM antes del servicio."
            if result.get("validation_status") == "PENDING_REVIEW"
            else "Dato respaldado por experiencia registrada del taller. Confirmar nivel final según procedimiento técnico."
        )
        return {"status": "ok", "vehicle": result}
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
              SUM(CASE WHEN validation_status = 'WORKSHOP_CONFIRMED' THEN 1 ELSE 0 END) AS workshop_confirmed
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
