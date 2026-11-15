"""Tests del catálogo y la importación sobre una copia del SQLite del repo.

Usan sqlite3 directo (misma interfaz que app.db.database.Database), así que
corren sin SQLAlchemy ni FastAPI instalados.
"""
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.catalog import service  # noqa: E402
from app.importers.consolidated import import_data  # noqa: E402


class SqliteDb:
    def __init__(self, connection):
        self.connection = connection

    def all(self, sql, params=None):
        return [dict(row) for row in self.connection.execute(sql, params or {})]

    def one(self, sql, params=None):
        row = self.connection.execute(sql, params or {}).fetchone()
        return dict(row) if row is not None else None

    def execute(self, sql, params=None):
        return self.connection.execute(sql, params or {}).rowcount


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        path = Path(cls.tmp) / "test.db"
        shutil.copy(ROOT / "atf_assistant.db", path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        # Lo que hace la migración 0001 sobre la base histórica.
        present = {row[1] for row in connection.execute("PRAGMA table_info(consolidated_atf_data)")}
        for column, kind in (("reviewed_at", "DATETIME"), ("reviewed_by", "TEXT"), ("review_notes", "TEXT")):
            if column not in present:
                connection.execute(f"ALTER TABLE consolidated_atf_data ADD COLUMN {column} {kind}")
        cls.db = SqliteDb(connection)
        import_data(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.connection.close()
        shutil.rmtree(cls.tmp)

    def test_vehiculos(self):
        vehicles = service.list_vehicles(self.db)
        self.assertGreater(len(vehicles), 100)
        detail = service.get_vehicle(self.db, vehicles[0]["id"])
        self.assertIn(detail["technical_data_status"], {"AVAILABLE", "PENDING_REVIEW"})
        self.assertIsNone(service.get_vehicle(self.db, 999999))

    def test_vehiculo_con_fluido(self):
        row = self.db.one(
            "SELECT vt.vehicle_variant_id AS id FROM transmission_fluid_data tfd "
            "JOIN vehicle_transmissions vt ON vt.id = tfd.vehicle_transmission_id LIMIT 1"
        )
        detail = service.get_vehicle(self.db, row["id"])
        self.assertEqual(detail["technical_data_status"], "AVAILABLE")
        self.assertIsNotNone(detail["fluid_data"]["specification"])

    def test_catalogo_y_filtros(self):
        everything = service.list_catalog(self.db)
        self.assertEqual(len(everything), 181)
        jeep = service.list_catalog(self.db, brand="jeep", model="comp")
        self.assertTrue(jeep and all(r["model"] == "Compass" for r in jeep))
        self.assertEqual(service.list_catalog(self.db, model="%"), [])
        pending = service.list_catalog(self.db, pending_only=True)
        self.assertTrue(all(r["validation_status"] == "PENDING_REVIEW" for r in pending))
        labels = {r["year_to"] for r in everything}
        self.assertIn("Actual", labels)  # year_to_label cuando no hay año

    def test_stats(self):
        stats = service.stats(self.db)
        self.assertEqual(stats["technical_references"], 181)
        self.assertEqual(stats["workshop_confirmed"], 14)

    def test_revision_manual_sobrevive_reimportacion(self):
        record_id = service.list_catalog(self.db, brand="Jeep")[0]["id"]
        result = service.review_catalog_record(self.db, record_id, "REJECTED", "Joel", "prueba")
        self.assertEqual(result["validation_status"], "REJECTED")
        import_data(self.db)
        self.assertEqual(service.get_catalog_record(self.db, record_id)["validation_status"], "REJECTED")
        self.assertIsNone(service.review_catalog_record(self.db, 999999, "REJECTED", "Joel", None))


if __name__ == "__main__":
    unittest.main()
