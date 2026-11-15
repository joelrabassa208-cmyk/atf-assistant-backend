"""Importa las planillas de data/ (taller real + referencia técnica) y las vincula."""
import re
import unicodedata

from app.config import BASE_DIR
from app.db.database import Database

WORKSHOP_FILE = BASE_DIR / "data" / "taller_real.md"
REFERENCE_FILE = BASE_DIR / "data" / "referencia_tecnica.md"


def split_row(line):
    return [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]


def is_separator(row):
    return all(re.fullmatch(r":?-+:?", cell) or cell == "-" for cell in row)


def normalize(value):
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def number(value):
    match = re.search(r"\d+(?:[.,]\d+)?", value or "")
    return float(match.group(0).replace(",", ".")) if match else None


def money(value):
    text = (value or "").replace("$", "").replace(".", "").replace(",", ".")
    text = re.sub(r"[^0-9.-]", "", text)
    return float(text) if text and text not in {"-", ".", "-."} else None


def year(value):
    match = re.search(r"\b(19|20)\d{2}\b", value or "")
    return int(match.group(0)) if match else None


def load_workshop():
    rows = [split_row(line) for line in WORKSHOP_FILE.read_text(encoding="utf-8").splitlines() if line.strip().startswith("|")]
    result = []
    for source_row, row in enumerate(rows[2:], start=3):
        if len(row) < 13 or is_separator(row) or not row[1]:
            continue
        result.append({
            "source_row": source_row,
            "legacy_id": row[0],
            "vehicle": row[1],
            "nishimoto_price": money(row[2]),
            "liqui_moly_price": money(row[3]),
            "motul_price": money(row[4]),
            "valvoline_price": money(row[5]),
            "mannol_price": money(row[6]),
            "liters": number(row[7]),
            "atf": row[8],
            "filter_1": row[9],
            "filter_2": row[10],
            "notes": row[11],
            "status": row[12],
        })
    return result


def load_reference():
    rows = [split_row(line) for line in REFERENCE_FILE.read_text(encoding="utf-8").splitlines() if line.strip().startswith("|")]
    result = []
    source_row = 0
    for row in rows:
        if len(row) < 10 or is_separator(row) or not row[0] or not row[1]:
            continue
        source_row += 1
        result.append({
            "source_row": source_row,
            "brand": row[0],
            "model": row[1],
            "engine": row[2],
            "year_from": year(row[3]),
            "year_to": year(row[4]),
            "year_to_label": row[4],
            "transmission_type": row[5],
            "transmission_code": row[6],
            "reference_liters": number(row[7]),
            "oem_specification": row[8],
            "suggested_product": row[9],
        })
    return result


GENERIC_CODES = {"", "AT", "CVT", "6AT", "8AT", "DCT", "ECVT", "DSG"}

DCT_WORDS = {"DSG", "DCT", "STRONIC", "S", "POWERSHIFT", "EDC", "DPS6"}
CVT_WORDS = {"CVT", "ECVT", "MULTITRONIC", "XTRONIC", "LINEARTRONIC"}
AT_WORDS = {"AT", "TIPTRONIC", "STEPTRONIC", "AL4", "EAT6", "EAT8", "MARCHAS"}


def words(value):
    return set(normalize(value).split())


def displacements(value):
    """Cilindradas tipo 1.4 / 2.0 presentes en el texto (1.4T, 2.0D, etc.)."""
    return set(re.findall(r"(?<![\d.])([1-6][.,]\d)(?!\d)", value or ""))


def gear_count(value):
    """Cantidad de marchas deducible del texto de la caja, o None."""
    text = normalize(value)
    patterns = [
        r"\b(\d{1,2}) ?(?:AT|HP|G TRONIC|MARCHAS|SPEED)\b",
        r"\b(\d{1,2})(?:T|F|L|R)\d{2}E?\b",     # 6T40, 6F35, 6L50, 6R80, 10R80
        r"\b(\d)HP\d{2}",                       # 6HP19, 8HP45
        r"\bZF ?(\d)(?:HP|H)?",                   # ZF9, ZF8HP, ZF 9H
        r"\b(?:AT|EAT|AW|ATX) ?(\d{1,2})\b",     # AT6, EAT6
        r"\bAL(4)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            gears = int(match.group(1))
            if 3 <= gears <= 10:
                return gears
    return None


def transmission_family(value):
    tokens = words(value)
    text = normalize(value)
    if tokens & CVT_WORDS:
        return "CVT"
    if tokens & DCT_WORDS or re.search(r"\bD[QL]\d{3}\b", text) or "S TRONIC" in text:
        return "DCT"
    if tokens & AT_WORDS or gear_count(value) or re.search(r"\b(ZF|AISIN)", text):
        return "AT"
    return None


BOX_MAKERS = ("ZF", "AISIN", "JATCO", "GETRAG")


def box_maker(value):
    text = normalize(value)
    found = {maker for maker in BOX_MAKERS if re.search(rf"\b{maker}", text)}
    return found.pop() if len(found) == 1 else None


def match_score(reference, workshop, sibling_models=()):
    """Puntaje de coincidencia; -1 si hay datos que se contradicen.

    Trabaja con palabras completas (no substrings) y descarta pares cuya
    cilindrada, tipo de caja o cantidad de marchas no coinciden.
    """
    description = workshop["vehicle"]
    desc_words = words(description)
    brand_words = words(reference["brand"])
    model_words = words(reference["model"])
    if not brand_words or not model_words or not brand_words <= desc_words:
        return -1
    if not model_words <= desc_words:
        return -1
    # "C4" no debe tomar un registro de "C4 LOUNGE" si existe ese modelo aparte.
    for sibling in sibling_models:
        if model_words < sibling and sibling <= desc_words:
            return -1
    score = 8

    reference_box = f"{reference['transmission_type']} {reference['transmission_code']}"
    ref_disp = displacements(reference["engine"])
    desc_disp = displacements(description)
    if ref_disp and desc_disp:
        if not ref_disp & desc_disp:
            return -1
        score += 3

    ref_family = transmission_family(reference_box)
    desc_family = transmission_family(description)
    if ref_family and desc_family:
        if ref_family != desc_family:
            return -1
        score += 1

    ref_maker = box_maker(reference_box)
    desc_maker = box_maker(description)
    if ref_maker and desc_maker and ref_maker != desc_maker:
        return -1

    ref_gears = gear_count(reference_box) or gear_count(reference["engine"])
    desc_gears = gear_count(description)
    if ref_gears and desc_gears:
        if ref_gears != desc_gears:
            return -1
        score += 2

    code = normalize(reference["transmission_code"])
    if code not in GENERIC_CODES and code in normalize(description):
        score += 6
    if "ACTUALIZADO" in (workshop["status"] or "").upper():
        score += 1
    return score


def choose_match(reference, workshop_rows, sibling_models=()):
    ranked = sorted(
        ((match_score(reference, row, sibling_models), row) for row in workshop_rows),
        key=lambda item: item[0],
        reverse=True,
    )
    ranked = [item for item in ranked if item[0] >= 8]
    if not ranked:
        return None, "SIN_COINCIDENCIA", "Falta experiencia del taller vinculada"
    best_score, best = ranked[0]
    ambiguous = len(ranked) > 1 and ranked[1][0] == best_score
    # ALTA exige modelo + cilindrada + al menos un dato de caja coincidente.
    confidence = "REVISAR_COINCIDENCIA" if ambiguous else ("ALTA" if best_score >= 12 else "PROBABLE")
    reasons = []
    if ambiguous:
        reasons.append("Hay más de una coincidencia posible")
    if best["liters"] is not None and reference["reference_liters"] is not None:
        if abs(best["liters"] - reference["reference_liters"]) >= 2:
            reasons.append("Diferencia de litros igual o mayor a 2")
    if normalize(reference["transmission_code"]) in GENERIC_CODES:
        reasons.append("Código de transmisión genérico")
    return best, confidence, "; ".join(reasons)


WORKSHOP_UPSERT = """
    INSERT INTO workshop_records (
      source_row, legacy_id, vehicle_description, liters_used, atf_used,
      filter_1, filter_2, notes, original_status, nishimoto_price,
      liqui_moly_price, motul_price, valvoline_price, mannol_price
    ) VALUES (
      :source_row, :legacy_id, :vehicle, :liters, :atf, :filter_1, :filter_2, :notes,
      :status, :nishimoto_price, :liqui_moly_price, :motul_price, :valvoline_price,
      :mannol_price
    )
    ON CONFLICT(source_row) DO UPDATE SET
      legacy_id=excluded.legacy_id,
      vehicle_description=excluded.vehicle_description,
      liters_used=excluded.liters_used,
      atf_used=excluded.atf_used,
      filter_1=excluded.filter_1,
      filter_2=excluded.filter_2,
      notes=excluded.notes,
      original_status=excluded.original_status,
      nishimoto_price=excluded.nishimoto_price,
      liqui_moly_price=excluded.liqui_moly_price,
      motul_price=excluded.motul_price,
      valvoline_price=excluded.valvoline_price,
      mannol_price=excluded.mannol_price
"""

REFERENCE_UPSERT = """
    INSERT INTO technical_reference_records (
      source_row, brand, model, engine, year_from, year_to, year_to_label,
      transmission_type, transmission_code, reference_liters,
      oem_specification, suggested_product
    ) VALUES (
      :source_row, :brand, :model, :engine, :year_from, :year_to, :year_to_label,
      :transmission_type, :transmission_code, :reference_liters,
      :oem_specification, :suggested_product
    )
    ON CONFLICT(source_row) DO UPDATE SET
      brand=excluded.brand, model=excluded.model, engine=excluded.engine,
      year_from=excluded.year_from, year_to=excluded.year_to,
      year_to_label=excluded.year_to_label,
      transmission_type=excluded.transmission_type,
      transmission_code=excluded.transmission_code,
      reference_liters=excluded.reference_liters,
      oem_specification=excluded.oem_specification,
      suggested_product=excluded.suggested_product
"""

# Las revisiones manuales (reviewed_at no nulo) no se pisan.
CONSOLIDATED_UPSERT = """
    INSERT INTO consolidated_atf_data (
      technical_reference_id, workshop_record_id, match_confidence,
      review_reason, validation_status
    ) VALUES (:technical_id, :workshop_id, :confidence, :reason, :validation)
    ON CONFLICT(technical_reference_id) DO UPDATE SET
      workshop_record_id=excluded.workshop_record_id,
      match_confidence=excluded.match_confidence,
      review_reason=excluded.review_reason,
      validation_status=excluded.validation_status
    WHERE consolidated_atf_data.reviewed_at IS NULL
"""


def _delete_missing(db: Database, table: str, keep: set[int]):
    """Borra filas que ya no existen en la planilla."""
    for row in db.all(f"SELECT id, source_row FROM {table}"):
        if row["source_row"] not in keep:
            db.execute(f"DELETE FROM {table} WHERE id = :id", {"id": row["id"]})


def import_data(db: Database):
    workshop_rows = load_workshop()
    reference_rows = load_reference()
    siblings = {}
    for row in reference_rows:
        siblings.setdefault(normalize(row["brand"]), set()).add(frozenset(words(row["model"])))

    _delete_missing(db, "workshop_records", {row["source_row"] for row in workshop_rows})
    _delete_missing(db, "technical_reference_records", {row["source_row"] for row in reference_rows})

    for row in workshop_rows:
        db.execute(WORKSHOP_UPSERT, {k: row[k] for k in (
            "source_row", "legacy_id", "vehicle", "liters", "atf", "filter_1", "filter_2",
            "notes", "status", "nishimoto_price", "liqui_moly_price", "motul_price",
            "valvoline_price", "mannol_price")})
    workshop_ids = {
        row["source_row"]: row["id"]
        for row in db.all("SELECT id, source_row FROM workshop_records")
    }

    for row in reference_rows:
        db.execute(REFERENCE_UPSERT, row)
        technical_id = db.one(
            "SELECT id FROM technical_reference_records WHERE source_row = :source_row",
            {"source_row": row["source_row"]},
        )["id"]
        best, confidence, reason = choose_match(row, workshop_rows, siblings[normalize(row["brand"])])
        workshop_id = workshop_ids[best["source_row"]] if best else None
        validation = "WORKSHOP_CONFIRMED" if best and confidence == "ALTA" and not reason else "PENDING_REVIEW"
        db.execute(CONSOLIDATED_UPSERT, {
            "technical_id": technical_id, "workshop_id": workshop_id,
            "confidence": confidence, "reason": reason, "validation": validation,
        })
    return {"workshop": len(workshop_rows), "reference": len(reference_rows)}


if __name__ == "__main__":
    from app.db.database import session

    with session() as database:
        counts = import_data(database)
    print(f"Registros del taller: {counts['workshop']}")
    print(f"Referencias técnicas: {counts['reference']}")
