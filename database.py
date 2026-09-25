import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "atf_assistant.db"

def get_connection():
    con = sqlite3.connect(DATABASE_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def create_database():
    con = get_connection()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS brands (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      country TEXT
    );
    CREATE TABLE IF NOT EXISTS models (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      brand_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE CASCADE,
      UNIQUE(brand_id,name)
    );
    CREATE TABLE IF NOT EXISTS vehicle_variants (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      model_id INTEGER NOT NULL,
      market TEXT NOT NULL DEFAULT 'Argentina',
      year_from INTEGER, year_to INTEGER, version TEXT,
      engine TEXT, fuel TEXT, drivetrain TEXT, notes TEXT,
      FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS transmissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      manufacturer TEXT, code TEXT, type TEXT, gears INTEGER, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS sources (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_type TEXT NOT NULL, publisher TEXT, title TEXT NOT NULL,
      document_year INTEGER, url TEXT, reference TEXT,
      checked_at DATETIME DEFAULT CURRENT_TIMESTAMP, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS vehicle_transmissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      vehicle_variant_id INTEGER NOT NULL,
      transmission_id INTEGER NOT NULL,
      validation_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
      source_id INTEGER, notes TEXT,
      FOREIGN KEY(vehicle_variant_id) REFERENCES vehicle_variants(id) ON DELETE CASCADE,
      FOREIGN KEY(transmission_id) REFERENCES transmissions(id) ON DELETE CASCADE,
      FOREIGN KEY(source_id) REFERENCES sources(id),
      UNIQUE(vehicle_variant_id,transmission_id)
    );
    CREATE TABLE IF NOT EXISTS fluids (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      manufacturer TEXT, name TEXT, specification TEXT, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS transmission_fluid_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      vehicle_transmission_id INTEGER NOT NULL,
      fluid_id INTEGER, specification TEXT,
      total_capacity_l REAL, service_capacity_l REAL,
      level_check_method TEXT,
      validation_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
      source_id INTEGER, notes TEXT,
      FOREIGN KEY(vehicle_transmission_id) REFERENCES vehicle_transmissions(id) ON DELETE CASCADE,
      FOREIGN KEY(fluid_id) REFERENCES fluids(id),
      FOREIGN KEY(source_id) REFERENCES sources(id)
    );
    CREATE TABLE IF NOT EXISTS procedures (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      vehicle_transmission_id INTEGER NOT NULL,
      procedure_type TEXT NOT NULL, name TEXT NOT NULL, description TEXT,
      validation_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
      source_id INTEGER,
      FOREIGN KEY(vehicle_transmission_id) REFERENCES vehicle_transmissions(id) ON DELETE CASCADE,
      FOREIGN KEY(source_id) REFERENCES sources(id)
    );
    CREATE TABLE IF NOT EXISTS procedure_steps (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      procedure_id INTEGER NOT NULL, step_number INTEGER NOT NULL,
      title TEXT NOT NULL, instruction TEXT NOT NULL, warning TEXT,
      requires_confirmation INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY(procedure_id) REFERENCES procedures(id) ON DELETE CASCADE,
      UNIQUE(procedure_id,step_number)
    );
    CREATE TABLE IF NOT EXISTS vins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      vehicle_variant_id INTEGER NOT NULL,
      vin TEXT NOT NULL UNIQUE, is_demo INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(vehicle_variant_id) REFERENCES vehicle_variants(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS workshop_records (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_row INTEGER NOT NULL UNIQUE,
      legacy_id TEXT,
      vehicle_description TEXT NOT NULL,
      liters_used REAL,
      atf_used TEXT,
      filter_1 TEXT,
      filter_2 TEXT,
      notes TEXT,
      original_status TEXT,
      nishimoto_price REAL,
      liqui_moly_price REAL,
      motul_price REAL,
      valvoline_price REAL,
      mannol_price REAL,
      imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS technical_reference_records (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_row INTEGER NOT NULL UNIQUE,
      brand TEXT NOT NULL,
      model TEXT NOT NULL,
      engine TEXT,
      year_from INTEGER,
      year_to INTEGER,
      year_to_label TEXT,
      transmission_type TEXT,
      transmission_code TEXT,
      reference_liters REAL,
      oem_specification TEXT,
      suggested_product TEXT,
      imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS consolidated_atf_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      technical_reference_id INTEGER NOT NULL UNIQUE,
      workshop_record_id INTEGER,
      match_confidence TEXT NOT NULL DEFAULT 'SIN_COINCIDENCIA',
      review_reason TEXT,
      validation_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
      FOREIGN KEY(technical_reference_id) REFERENCES technical_reference_records(id) ON DELETE CASCADE,
      FOREIGN KEY(workshop_record_id) REFERENCES workshop_records(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_models_brand ON models(brand_id);
    CREATE INDEX IF NOT EXISTS idx_variants_model ON vehicle_variants(model_id);
    CREATE INDEX IF NOT EXISTS idx_vins_vin ON vins(vin);
    CREATE INDEX IF NOT EXISTS idx_workshop_vehicle ON workshop_records(vehicle_description);
    CREATE INDEX IF NOT EXISTS idx_reference_vehicle ON technical_reference_records(brand,model,engine);
    CREATE INDEX IF NOT EXISTS idx_consolidated_status ON consolidated_atf_data(validation_status);
    """)
    con.commit()
    con.close()

if __name__ == "__main__":
    create_database()
    print("ATF ASSISTANT DATABASE V1")
    print("Base de datos creada correctamente")
    print(DATABASE_PATH)
