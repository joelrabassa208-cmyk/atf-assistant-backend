from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.catalog import service
from app.db.database import Database, get_db
from app.security import require_admin_key

router = APIRouter()


class ReviewRequest(BaseModel):
    validation_status: Literal["WORKSHOP_CONFIRMED", "PENDING_REVIEW", "REJECTED"]
    reviewed_by: str = Field(min_length=1, max_length=100)
    review_notes: str | None = Field(default=None, max_length=1000)


@router.get("/api/vehicles")
def get_vehicles(db: Database = Depends(get_db)):
    vehicles = service.list_vehicles(db)
    return {"status": "ok", "count": len(vehicles), "vehicles": vehicles}


@router.get("/api/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: int, db: Database = Depends(get_db)):
    vehicle = service.get_vehicle(db, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return {"status": "ok", "vehicle": vehicle}


@router.get("/api/atf-catalog")
def get_atf_catalog(
    brand: str | None = None,
    model: str | None = None,
    pending_only: bool = False,
    db: Database = Depends(get_db),
):
    rows = service.list_catalog(db, brand, model, pending_only)
    return {"status": "ok", "count": len(rows), "vehicles": rows}


@router.get("/api/atf-catalog/{record_id}")
def get_atf_catalog_record(record_id: int, db: Database = Depends(get_db)):
    record = service.get_catalog_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
    return {"status": "ok", "vehicle": record}


@router.patch("/api/atf-catalog/{record_id}/review", dependencies=[Depends(require_admin_key)])
def review_atf_catalog_record(record_id: int, review: ReviewRequest, db: Database = Depends(get_db)):
    """Revisión manual. La importación al arrancar no la pisa."""
    record = service.review_catalog_record(
        db, record_id, review.validation_status, review.reviewed_by, review.review_notes
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Registro ATF no encontrado")
    return {"status": "ok", "vehicle": record}


@router.get("/api/atf-stats")
def get_atf_stats(db: Database = Depends(get_db)):
    return {"status": "ok", "stats": service.stats(db)}
