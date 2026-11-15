"""Lote técnico v1.4: Chevrolet, Ford y Toyota.

Solo carga datos respaldados por documentación oficial. Las capacidades
indicadas como "total" son capacidades de referencia/seco, no cantidades de
servicio. Nunca deben emplearse como volumen automático de reposición.
"""

from database import create_database, get_connection


SOURCES = {
    "chev_onix_2025": (
        "Chevrolet Argentina", "Manual del propietario Onix 2025", 2025,
        "https://www.chevrolet.com.ar/content/dam/chevrolet/sa/argentina/espanol/index/manuals/pdf/onix/2025/onix-manual-del-propietario-2025.pdf",
    ),
    "chev_spin_2025": (
        "Chevrolet Argentina", "Manual del propietario Spin 2025", 2025,
        "https://www.chevrolet.com.ar/content/dam/chevrolet/sa/argentina/espanol/index/manuals/pdf/spin/2025/manual-propietario/Spin-manual-del-propietario-2025.pdf",
    ),
    "chev_s10_2025": (
        "Chevrolet Argentina", "Manual del propietario S10 2025", 2025,
        "https://www.chevrolet.com.ar/content/dam/chevrolet/sa/argentina/espanol/index/manuals/pdf/s10/2025/manual-propietario/s10-manual-de-propietario-2025.pdf",
    ),
    "ford_ranger_6r80": (
        "Ford Argentina", "Programa de mantenimiento Ranger - líquidos del vehículo", None,
        "https://www.ford.com.ar/content/dam/Ford/website-assets/latam/ar/posventa/mantenimientos%20programados/ranger/far-ranger-garantia-y-mantenimineto.pdf",
    ),
    "ford_dps6": (
        "Ford Motor Company", "Motorcraft Dual Clutch Transmission Fluid XT-11-QDC", None,
        "https://www.ford.com/product/automatic-transmission-fluid-p4000151268",
    ),
    "toyota_hilux": (
        "Toyota Argentina", "Manual del propietario Hilux - datos técnicos", 2022,
        "https://media.toyota.com.ar/04f25283-6787-4fdb-bc62-fc133c9086bc.pdf",
    ),
}


def source(con, key):
    publisher, title, year, url = SOURCES[key]
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if row:
        return row[0]
    return con.execute(
        """INSERT INTO sources(source_type,publisher,title,document_year,url,notes)
           VALUES('OWNER_MANUAL',?,?,?,?,?)""",
        (publisher, title, year, url, "Fuente oficial revisada para lote técnico v1.4."),
    ).lastrowid


def fluid(con, maker, name, spec):
    row = con.execute(
        "SELECT id FROM fluids WHERE manufacturer=? AND name=? AND specification=?",
        (maker, name, spec),
    ).fetchone()
    if row:
        return row[0]
    return con.execute(
        "INSERT INTO fluids(manufacturer,name,specification,notes) VALUES(?,?,?,?)",
        (maker, name, spec, "Especificación oficial; validar producto comercial equivalente."),
    ).lastrowid


def variants(con, brand, model, year_from=None, year_to=None, transmission_code=None):
    sql = """SELECT v.id,vt.id AS vt_id FROM vehicle_variants v
             JOIN models m ON m.id=v.model_id JOIN brands b ON b.id=m.brand_id
             JOIN vehicle_transmissions vt ON vt.vehicle_variant_id=v.id
             LEFT JOIN transmissions t ON t.id=vt.transmission_id
             WHERE b.name=? AND m.name=?"""
    args = [brand, model]
    if year_from is not None:
        sql += " AND v.year_from=?"; args.append(year_from)
    if year_to is not None:
        sql += " AND v.year_to=?"; args.append(year_to)
    if transmission_code is not None:
        sql += " AND t.code=?"; args.append(transmission_code)
    return con.execute(sql, args).fetchall()


def add_fluid(con, vt_id, fluid_id, source_id, specification, total=None,
              service=None, level=None, notes=None):
    con.execute("DELETE FROM transmission_fluid_data WHERE vehicle_transmission_id=?", (vt_id,))
    con.execute(
        """INSERT INTO transmission_fluid_data
           (vehicle_transmission_id,fluid_id,specification,total_capacity_l,
            service_capacity_l,level_check_method,validation_status,source_id,notes)
           VALUES(?,?,?,?,?,?, 'VERIFIED_OFFICIAL',?,?)""",
        (vt_id, fluid_id, specification, total, service, level, source_id, notes),
    )
    con.execute(
        "UPDATE vehicle_transmissions SET validation_status='VERIFIED_OFFICIAL' WHERE id=?",
        (vt_id,),
    )


def split_chevrolet_year(con, model, old_from, old_to, target_year):
    """Aísla el año documentado y deja el resto pendiente."""
    rows = con.execute(
        """SELECT v.*,vt.transmission_id FROM vehicle_variants v
           JOIN models m ON m.id=v.model_id JOIN brands b ON b.id=m.brand_id
           JOIN vehicle_transmissions vt ON vt.vehicle_variant_id=v.id
           WHERE b.name='Chevrolet' AND m.name=? AND v.year_from=? AND v.year_to=?""",
        (model, old_from, old_to),
    ).fetchall()
    if not rows:
        return
    r = rows[0]
    con.execute("UPDATE vehicle_variants SET year_to=? WHERE id=?", (target_year - 1, r['id']))
    for y1, y2 in ((target_year, target_year), (target_year + 1, old_to)):
        if y1 > y2:
            continue
        cur = con.execute(
            """INSERT INTO vehicle_variants
               (model_id,market,year_from,year_to,version,engine,fuel,drivetrain,notes)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (r['model_id'], r['market'], y1, y2, r['version'], r['engine'], r['fuel'],
             r['drivetrain'], "Segmentado por año para validación técnica v1.4."),
        )
        con.execute(
            """INSERT INTO vehicle_transmissions
               (vehicle_variant_id,transmission_id,validation_status,notes)
               VALUES(?,?,'PENDING_REVIEW',?)""",
            (cur.lastrowid, r['transmission_id'], "Validar por VIN antes del servicio."),
        )


def seed():
    create_database()
    con = get_connection()
    try:
        # Separa los únicos años Chevrolet cubiertos por los manuales revisados.
        split_chevrolet_year(con, "Onix", 2020, 2026, 2025)
        split_chevrolet_year(con, "Spin", 2013, 2026, 2025)
        split_chevrolet_year(con, "S10", 2012, 2026, 2025)

        dex6 = fluid(con, "ACDelco / GM", "DEXRON VI", "DEXRON VI")
        dexhp = fluid(con, "ACDelco / GM", "DEXRON HP", "DEXRON HP")
        mercon = fluid(con, "Motorcraft", "MERCON LV", "Ford WSS-M2C938-A")
        dct = fluid(con, "Motorcraft", "Dual Clutch Transmission Fluid XT-11-QDC", "Ford WSS-M2C200-D2")
        ws = fluid(con, "Toyota", "Genuine ATF WS", "Toyota ATF WS")

        for model, src_key in (("Onix", "chev_onix_2025"), ("Spin", "chev_spin_2025")):
            for r in variants(con, "Chevrolet", model, 2025, 2025):
                add_fluid(con, r['vt_id'], dex6, source(con, src_key), "DEXRON VI",
                          notes="Manual oficial 2025. Capacidad y método de nivel no publicados en esta fuente; permanecen pendientes.")
        for r in variants(con, "Chevrolet", "S10", 2025, 2025):
            add_fluid(con, r['vt_id'], dexhp, source(con, "chev_s10_2025"), "DEXRON HP",
                      notes="Manual oficial 2025: cambio indicado cada 70.000 km. Capacidad y método de nivel pendientes.")

        for r in variants(con, "Ford", "Ranger", 2012, 2022, "6R80"):
            add_fluid(con, r['vt_id'], mercon, source(con, "ford_ranger_6r80"), "Ford WSS-M2C938-A",
                      total=10.5, service=None,
                      notes="10,5 L es capacidad seca; el documento también informa 9,0 L húmeda. No usar como reposición automática.")

        # Corrige registros anteriores: 9,0 L "húmeda" no equivale a una
        # cantidad de servicio y no debe mostrarse como tal.
        con.execute(
            """UPDATE transmission_fluid_data SET service_capacity_l=NULL,
               notes=COALESCE(notes || ' ', '') ||
               'La cifra 9,0 L húmeda no es una cantidad automática de servicio.'
               WHERE id IN (
                 SELECT tfd.id FROM transmission_fluid_data tfd
                 JOIN vehicle_transmissions vt ON vt.id=tfd.vehicle_transmission_id
                 JOIN vehicle_variants v ON v.id=vt.vehicle_variant_id
                 JOIN models m ON m.id=v.model_id JOIN brands b ON b.id=m.brand_id
                 JOIN transmissions t ON t.id=vt.transmission_id
                 WHERE b.name='Ford' AND m.name='Ranger' AND t.code='6R80'
                   AND tfd.service_capacity_l=9.0
               )"""
        )

        for model in ("Fiesta", "Focus", "EcoSport"):
            for r in variants(con, "Ford", model, transmission_code="DPS6"):
                add_fluid(con, r['vt_id'], dct, source(con, "ford_dps6"), "Ford WSS-M2C200-D2",
                          notes="Caja de doble embrague seco. No tratar como una automática convencional ni realizar diálisis ATF.")

        for r in variants(con, "Toyota", "Hilux", 2023, 2023):
            add_fluid(con, r['vt_id'], ws, source(con, "toyota_hilux"), "Toyota ATF WS",
                      total=9.5, service=None,
                      notes="9,5 L es volumen total de referencia del manual, no volumen de drenaje ni reposición.")

        con.commit()
        print("Lote técnico v1.4 aplicado")
    finally:
        con.close()


if __name__ == "__main__":
    seed()
