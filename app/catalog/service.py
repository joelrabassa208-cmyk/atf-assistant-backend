"""Consultas del catálogo técnico (global, compartido por todos los talleres).

SQL portable SQLite/Postgres con parámetros con nombre.
"""
from __future__ import annotations

from app.db.database import Database

VEHICLES_SQL = """
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
    JOIN models m ON m.id = v.model_id
    JOIN brands b ON b.id = m.brand_id
    LEFT JOIN vehicle_transmissions vt ON vt.vehicle_variant_id = v.id
    LEFT JOIN transmissions t ON t.id = vt.transmission_id
    ORDER BY b.name, m.name, v.year_from, v.version, v.id
"""

VEHICLE_SQL = """
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
    JOIN models m ON m.id = v.model_id
    JOIN brands b ON b.id = m.brand_id
    LEFT JOIN vehicle_transmissions vt ON vt.vehicle_variant_id = v.id
    LEFT JOIN transmissions t ON t.id = vt.transmission_id
    WHERE v.id = :id
    ORDER BY vt.id
"""

FLUID_SQL = """
    SELECT
        f.manufacturer AS fluid_manufacturer,
        f.name AS fluid_name,
        COALESCE(tfd.specification, f.specification) AS specification,
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
    LEFT JOIN fluids f ON f.id = tfd.fluid_id
    LEFT JOIN sources s ON s.id = tfd.source_id
    WHERE tfd.vehicle_transmission_id = :vt_id
    ORDER BY tfd.id DESC
    LIMIT 1
"""

# year_to (entero) y year_to_label (texto) se combinan en Python:
# Postgres no admite COALESCE entre tipos distintos.
CATALOG_SELECT = """
    SELECT
      tr.id, tr.brand, tr.model, tr.engine, tr.year_from,
      tr.year_to AS year_to_number, tr.year_to_label,
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
    JOIN consolidated_atf_data cad ON cad.technical_reference_id = tr.id
    LEFT JOIN workshop_records wr ON wr.id = cad.workshop_record_id
"""

STATS_SQL = """
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

SAFETY_NOTICES = {
    "PENDING_REVIEW": "Dato pendiente de revisión técnica. Confirmar código físico de caja y especificación OEM antes del servicio.",
    "REJECTED": "Registro descartado en revisión técnica. No usar como referencia.",
    "WORKSHOP_CONFIRMED": "Dato respaldado por experiencia registrada del taller. Confirmar nivel final según procedimiento técnico.",
}


def list_vehicles(db: Database):
    return db.all(VEHICLES_SQL)


def get_vehicle(db: Database, vehicle_id: int):
    vehicle = db.one(VEHICLE_SQL, {"id": vehicle_id})
    if vehicle is None:
        return None
    fluid = None
    if vehicle.get("vehicle_transmission_id") is not None:
        fluid = db.one(FLUID_SQL, {"vt_id": vehicle["vehicle_transmission_id"]})
    vehicle["fluid_data"] = fluid
    vehicle["technical_data_status"] = "AVAILABLE" if fluid is not None else "PENDING_REVIEW"
    return vehicle


def _catalog_row(row):
    year_to = row.pop("year_to_number")
    label = row.pop("year_to_label")
    row["year_to"] = year_to if year_to is not None else label
    return row


def list_catalog(db: Database, brand: str | None = None, model: str | None = None,
                 pending_only: bool = False):
    where, params = [], {}
    if brand:
        where.append("LOWER(tr.brand) = LOWER(:brand)")
        params["brand"] = brand
    if model:
        escaped = model.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("LOWER(tr.model) LIKE LOWER(:model) ESCAPE '\\'")
        params["model"] = f"%{escaped}%"
    if pending_only:
        where.append("cad.validation_status = 'PENDING_REVIEW'")
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = db.all(f"{CATALOG_SELECT} {clause} ORDER BY tr.brand, tr.model, tr.year_from, tr.engine, tr.id", params)
    return [_catalog_row(row) for row in rows]


def get_catalog_record(db: Database, record_id: int):
    row = db.one(CATALOG_SELECT + " WHERE tr.id = :id", {"id": record_id})
    if row is None:
        return None
    result = _catalog_row(row)
    workshop_liters = result.get("workshop_liters")
    result["recommended_service_liters"] = (
        workshop_liters if workshop_liters is not None else result.get("reference_liters")
    )
    result["service_liters_source"] = "WORKSHOP" if workshop_liters is not None else "REFERENCE"
    result["safety_notice"] = SAFETY_NOTICES.get(
        result.get("validation_status"), SAFETY_NOTICES["PENDING_REVIEW"]
    )
    return result


def review_catalog_record(db: Database, record_id: int, status: str, reviewed_by: str,
                          notes: str | None):
    updated = db.execute(
        """
        UPDATE consolidated_atf_data
        SET validation_status = :status, reviewed_by = :by, review_notes = :notes,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE technical_reference_id = :id
        """,
        {"status": status, "by": reviewed_by, "notes": notes, "id": record_id},
    )
    return get_catalog_record(db, record_id) if updated else None


def stats(db: Database):
    row = db.one(STATS_SQL)
    # SUM devuelve NULL sin filas; y Postgres puede devolver Decimal.
    return {key: int(value or 0) for key, value in row.items()}
