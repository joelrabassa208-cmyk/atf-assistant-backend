import sqlite3
from database import get_connection, create_database


SOURCES = {
    "Fiat": ("Sitio y documentación oficial Fiat Argentina", "https://www.fiat.com.ar/"),
    "Chevrolet": ("Manuales oficiales Chevrolet Argentina", "https://www.chevrolet.com.ar/manuales"),
    "Volkswagen": ("Sitio y documentación oficial Volkswagen Argentina", "https://www.volkswagen.com.ar/"),
    "Peugeot": ("Fichas técnicas y manuales Peugeot Argentina", "https://www.peugeot.com.ar/enlaces/fichas-tecnicas.html"),
    "Ford": ("Sitio y documentación oficial Ford Argentina", "https://www.ford.com.ar/"),
    "Honda": ("Sitio y documentación oficial Honda Argentina", "https://autos.honda.com.ar/"),
}

# Esta carga amplía el selector con familias frecuentes en Argentina. El estado
# PENDING_REVIEW es intencional: no convierte el nombre comercial de una caja
# en una especificación de fluido ni habilita datos técnicos no documentados.
VEHICLES = [
    # Marca, modelo, desde, hasta, versión, motor, combustible, tracción,
    # fabricante caja, código/familia, tipo, marchas
    ("Fiat", "Cronos", 2018, 2022, "Precision AT6", "1.8 16V E.torQ", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Fiat", "Cronos", 2022, 2026, "Drive / Precision CVT", "1.3 Firefly", "Nafta", "Delantera", "Aisin", "CVT", "CVT", None),
    ("Fiat", "Argo", 2018, 2021, "Precision AT6", "1.8 16V E.torQ", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Fiat", "Argo", 2022, 2026, "Drive CVT", "1.3 Firefly", "Nafta", "Delantera", "Aisin", "CVT", "CVT", None),
    ("Fiat", "Palio", 2008, 2017, "Dualogic", "1.6 16V E.torQ", "Nafta", "Delantera", "Magneti Marelli", "Dualogic", "Manual automatizada", 5),
    ("Fiat", "Grand Siena", 2012, 2021, "Dualogic", "1.6 16V E.torQ", "Nafta", "Delantera", "Magneti Marelli", "Dualogic", "Manual automatizada", 5),
    ("Fiat", "Punto", 2008, 2017, "Dualogic", "1.6 / 1.8 16V", "Nafta", "Delantera", "Magneti Marelli", "Dualogic", "Manual automatizada", 5),
    ("Fiat", "Idea", 2010, 2016, "Dualogic", "1.6 / 1.8 16V", "Nafta", "Delantera", "Magneti Marelli", "Dualogic", "Manual automatizada", 5),
    ("Fiat", "Strada", 2024, 2026, "Volcano / Ranch CVT", "1.3 Firefly", "Nafta", "Delantera", "Aisin", "CVT", "CVT", None),
    ("Fiat", "Toro", 2016, 2026, "Freedom / Volcano AT9", "2.0 Multijet", "Diésel", "4x4", "ZF", "9HP", "Automática", 9),
    ("Fiat", "Toro", 2022, 2026, "Turbo AT6", "1.3 Turbo", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),

    ("Chevrolet", "Corsa", 2000, 2012, "Automático", "1.6 8V", "Nafta", "Delantera", "GM", "AT4", "Automática", 4),
    ("Chevrolet", "Agile", 2012, 2016, "Easytronic", "1.4 8V", "Nafta", "Delantera", "Magneti Marelli", "Easytronic", "Manual automatizada", 5),
    ("Chevrolet", "Prisma", 2013, 2019, "LTZ AT6", "1.4 8V", "Nafta", "Delantera", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Onix", 2013, 2019, "LTZ AT6", "1.4 8V", "Nafta", "Delantera", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Onix", 2020, 2026, "Turbo AT6", "1.0 Turbo", "Nafta", "Delantera", "GM", "AT6", "Automática", 6),
    ("Chevrolet", "Cruze", 2011, 2016, "AT6", "1.8 16V", "Nafta", "Delantera", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Cruze", 2016, 2023, "Turbo AT6", "1.4 Turbo", "Nafta", "Delantera", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Spin", 2013, 2026, "AT6", "1.8 8V", "Nafta", "Delantera", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Tracker", 2013, 2020, "AWD AT6", "1.8 16V", "Nafta", "Integral", "GM", "GF6", "Automática", 6),
    ("Chevrolet", "Tracker", 2020, 2026, "Turbo AT6", "1.2 Turbo", "Nafta", "Delantera", "GM", "AT6", "Automática", 6),
    ("Chevrolet", "S10", 2012, 2026, "4x4 AT6", "2.8 Turbo Diésel", "Diésel", "4x4", "GM", "AT6", "Automática", 6),

    ("Volkswagen", "Gol Trend", 2010, 2019, "I-Motion", "1.6 MSI", "Nafta", "Delantera", "Magneti Marelli", "I-Motion", "Manual automatizada", 5),
    ("Volkswagen", "Voyage", 2010, 2019, "I-Motion", "1.6 MSI", "Nafta", "Delantera", "Magneti Marelli", "I-Motion", "Manual automatizada", 5),
    ("Volkswagen", "Fox", 2010, 2019, "I-Motion", "1.6 MSI", "Nafta", "Delantera", "Magneti Marelli", "I-Motion", "Manual automatizada", 5),
    ("Volkswagen", "Suran", 2010, 2019, "I-Motion", "1.6 MSI", "Nafta", "Delantera", "Magneti Marelli", "I-Motion", "Manual automatizada", 5),
    ("Volkswagen", "Polo", 2018, 2026, "Tiptronic", "1.6 MSI / 1.0 TSI", "Nafta", "Delantera", "Aisin", "AQ160", "Automática", 6),
    ("Volkswagen", "Virtus", 2018, 2026, "Tiptronic", "1.6 MSI / 1.0 TSI", "Nafta", "Delantera", "Aisin", "AQ160", "Automática", 6),
    ("Volkswagen", "Vento", 2006, 2014, "Tiptronic", "2.5", "Nafta", "Delantera", "Aisin", "09G", "Automática", 6),
    ("Volkswagen", "Vento", 2011, 2026, "DSG", "2.0 TSI", "Nafta", "Delantera", "Volkswagen", "DSG", "Doble embrague", 6),
    ("Volkswagen", "T-Cross", 2019, 2026, "Tiptronic", "1.0 TSI", "Nafta", "Delantera", "Aisin", "AQ160", "Automática", 6),
    ("Volkswagen", "Taos", 2021, 2025, "Tiptronic", "1.4 TSI", "Nafta", "Delantera", "Aisin", "AQ250", "Automática", 6),
    ("Volkswagen", "Taos", 2026, 2026, "Tiptronic", "1.4 TSI", "Nafta", "Delantera", "Aisin", "AT8", "Automática", 8),
    ("Volkswagen", "Amarok", 2012, 2026, "4Motion AT8", "2.0 BiTDI / 3.0 V6 TDI", "Diésel", "4x4", "ZF", "8HP", "Automática", 8),

    ("Peugeot", "206", 2001, 2009, "Automático", "1.6 16V", "Nafta", "Delantera", "PSA", "AL4", "Automática", 4),
    ("Peugeot", "207 Compact", 2009, 2016, "Automático", "1.6 16V", "Nafta", "Delantera", "PSA", "AL4", "Automática", 4),
    ("Peugeot", "208", 2013, 2020, "Tiptronic", "1.6 16V", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Peugeot", "208", 2020, 2024, "Tiptronic AT6", "1.6 16V", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Peugeot", "208", 2025, 2026, "Turbo CVT", "1.0 Turbo", "Nafta", "Delantera", "CVT", "CVT", "CVT", None),
    ("Peugeot", "307", 2001, 2011, "Tiptronic", "2.0 16V", "Nafta", "Delantera", "PSA", "AL4", "Automática", 4),
    ("Peugeot", "308", 2012, 2021, "Tiptronic", "1.6 / 2.0 16V", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Peugeot", "408", 2011, 2021, "Tiptronic", "1.6 THP / 2.0 16V", "Nafta", "Delantera", "Aisin", "AT6", "Automática", 6),
    ("Peugeot", "2008", 2016, 2024, "EAT6", "1.6 16V / 1.6 THP", "Nafta", "Delantera", "Aisin", "EAT6", "Automática", 6),
    ("Peugeot", "2008", 2025, 2026, "Turbo CVT", "1.0 Turbo", "Nafta", "Delantera", "CVT", "CVT", "CVT", None),
    ("Peugeot", "3008", 2010, 2026, "Tiptronic / EAT8", "1.6 THP", "Nafta", "Delantera", "Aisin", "EAT6-EAT8", "Automática", None),

    ("Ford", "Ka", 2019, 2021, "SEL AT6", "1.5 Ti-VCT", "Nafta", "Delantera", "Ford", "6F15", "Automática", 6),
    ("Ford", "Fiesta", 2011, 2018, "PowerShift", "1.6 Ti-VCT", "Nafta", "Delantera", "Getrag", "DPS6", "Doble embrague seca", 6),
    ("Ford", "Focus", 2013, 2019, "PowerShift", "2.0 Duratec", "Nafta", "Delantera", "Getrag", "DPS6", "Doble embrague seca", 6),
    ("Ford", "EcoSport", 2013, 2017, "PowerShift", "2.0 Duratec", "Nafta", "Delantera", "Getrag", "DPS6", "Doble embrague seca", 6),
    ("Ford", "EcoSport", 2018, 2021, "AT6", "1.5 Dragon / 2.0 GDI", "Nafta", "Delantera", "Ford", "6F15-6F35", "Automática", 6),
    ("Ford", "Territory", 2020, 2022, "CVT", "1.5 Turbo", "Nafta", "Delantera", "Jatco", "CVT", "CVT", None),
    ("Ford", "Territory", 2023, 2026, "DCT7", "1.8 Turbo", "Nafta", "Delantera", "Ford", "DCT7", "Doble embrague", 7),
    ("Ford", "Kuga", 2013, 2020, "AWD AT6", "1.6 / 2.0 EcoBoost", "Nafta", "Integral", "Ford", "6F35", "Automática", 6),
    ("Ford", "Maverick", 2022, 2026, "AT8 / eCVT", "2.0 EcoBoost / 2.5 Hybrid", "Nafta/Híbrido", "Delantera/Integral", "Ford", "8F35-eCVT", "Automática/eCVT", None),
    ("Ford", "Ranger", 2012, 2022, "4x4 AT6", "3.2 TDCi", "Diésel", "4x4", "Ford", "6R80", "Automática", 6),
    ("Ford", "Ranger", 2023, 2026, "4x4 AT10", "2.0 Bi-Turbo / 3.0 V6", "Diésel", "4x4", "Ford", "10R80", "Automática", 10),

    ("Honda", "Fit", 2009, 2021, "AT5 / CVT", "1.5 i-VTEC", "Nafta", "Delantera", "Honda", "AT5-CVT", "Automática/CVT", None),
    ("Honda", "City", 2010, 2026, "AT5 / CVT", "1.5 i-VTEC", "Nafta", "Delantera", "Honda", "AT5-CVT", "Automática/CVT", None),
    ("Honda", "Civic", 2006, 2016, "AT5", "1.8 i-VTEC", "Nafta", "Delantera", "Honda", "AT5", "Automática", 5),
    ("Honda", "Civic", 2017, 2026, "CVT", "2.0 / 1.5 Turbo", "Nafta", "Delantera", "Honda", "CVT", "CVT", None),
    ("Honda", "HR-V", 2015, 2026, "CVT", "1.8 / 1.5 i-VTEC", "Nafta", "Delantera", "Honda", "CVT", "CVT", None),
    ("Honda", "WR-V", 2018, 2022, "CVT", "1.5 i-VTEC", "Nafta", "Delantera", "Honda", "CVT", "CVT", None),
    ("Honda", "CR-V", 2007, 2016, "AT5", "2.4 i-VTEC", "Nafta", "Integral", "Honda", "AT5", "Automática", 5),
    ("Honda", "CR-V", 2017, 2026, "CVT", "1.5 Turbo", "Nafta", "Integral", "Honda", "CVT", "CVT", None),
    ("Honda", "Accord", 2008, 2017, "AT5 / AT6", "2.4 / 3.5", "Nafta", "Delantera", "Honda", "AT5-AT6", "Automática", None),
]


def get_or_create_source(con, brand):
    title, url = SOURCES[brand]
    row = con.execute("SELECT id FROM sources WHERE title = ?", (title,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        """INSERT INTO sources
           (source_type, publisher, title, url, notes)
           VALUES ('OFFICIAL_WEBSITE', ?, ?, ?, ?)""",
        (brand, title, url, "Fuente de marca para identificar gama. Cada dato técnico requiere validación específica."),
    )
    return cur.lastrowid


def get_or_create_brand(con, brand):
    con.execute("INSERT OR IGNORE INTO brands(name) VALUES (?)", (brand,))
    return con.execute("SELECT id FROM brands WHERE name = ?", (brand,)).fetchone()[0]


def get_or_create_model(con, brand_id, model):
    con.execute("INSERT OR IGNORE INTO models(brand_id, name) VALUES (?, ?)", (brand_id, model))
    return con.execute(
        "SELECT id FROM models WHERE brand_id = ? AND name = ?", (brand_id, model)
    ).fetchone()[0]


def get_or_create_transmission(con, maker, code, kind, gears):
    row = con.execute(
        """SELECT id FROM transmissions
           WHERE COALESCE(manufacturer, '') = COALESCE(?, '')
             AND COALESCE(code, '') = COALESCE(?, '')
             AND COALESCE(type, '') = COALESCE(?, '')
             AND COALESCE(gears, -1) = COALESCE(?, -1)""",
        (maker, code, kind, gears),
    ).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO transmissions(manufacturer, code, type, gears) VALUES (?, ?, ?, ?)",
        (maker, code, kind, gears),
    )
    return cur.lastrowid


def variant_exists(con, model_id, y1, y2, version, engine):
    return con.execute(
        """SELECT id FROM vehicle_variants
           WHERE model_id = ? AND COALESCE(year_from, -1) = COALESCE(?, -1)
             AND COALESCE(year_to, -1) = COALESCE(?, -1)
             AND COALESCE(version, '') = COALESCE(?, '')
             AND COALESCE(engine, '') = COALESCE(?, '')""",
        (model_id, y1, y2, version, engine),
    ).fetchone()


def seed():
    create_database()
    con = get_connection()
    inserted = 0
    try:
        for item in VEHICLES:
            brand, model, y1, y2, version, engine, fuel, drive, maker, code, kind, gears = item
            brand_id = get_or_create_brand(con, brand)
            model_id = get_or_create_model(con, brand_id, model)
            source_id = get_or_create_source(con, brand)
            if variant_exists(con, model_id, y1, y2, version, engine):
                continue
            cur = con.execute(
                """INSERT INTO vehicle_variants
                   (model_id, market, year_from, year_to, version, engine, fuel, drivetrain, notes)
                   VALUES (?, 'Argentina', ?, ?, ?, ?, ?, ?, ?)""",
                (model_id, y1, y2, version, engine, fuel, drive,
                 "Lote frecuente Argentina v1.3. Datos ATF y procedimiento pendientes de validación específica."),
            )
            transmission_id = get_or_create_transmission(con, maker, code, kind, gears)
            con.execute(
                """INSERT INTO vehicle_transmissions
                   (vehicle_variant_id, transmission_id, validation_status, source_id, notes)
                   VALUES (?, ?, 'PENDING_REVIEW', ?, ?)""",
                (cur.lastrowid, transmission_id, source_id,
                 "Aplicación incorporada al selector. Validar código exacto por año/VIN antes del servicio."),
            )
            inserted += 1
        con.commit()
        total = con.execute("SELECT COUNT(*) FROM vehicle_variants").fetchone()[0]
        print(f"Nuevas variantes: {inserted}")
        print(f"Total variantes: {total}")
    finally:
        con.close()


if __name__ == "__main__":
    seed()
