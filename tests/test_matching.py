"""Tests de la vinculación taller <-> referencia técnica.

Ejecutar con:  python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from import_consolidated_data import choose_match, match_score  # noqa: E402


def ref(brand, model, engine, code, kind="AT", liters=9.0):
    return {
        "brand": brand, "model": model, "engine": engine,
        "transmission_type": kind, "transmission_code": code,
        "reference_liters": liters,
    }


def shop(vehicle, liters=9.0, status="ACTUALIZADO"):
    return {"vehicle": vehicle, "liters": liters, "status": status, "source_row": 1}


class RejectsContradictions(unittest.TestCase):
    """Casos reales que la v1.5 marcaba como WORKSHOP_CONFIRMED por error."""

    def assertRejected(self, reference, workshop, siblings=()):
        self.assertEqual(match_score(reference, shop(workshop), siblings), -1)

    def test_distinta_cilindrada(self):
        self.assertRejected(ref("Jeep", "Compass", "2.0", "ZF 9HP"), "JEEP COMPASS 2.4 - CAJA AT6")
        self.assertRejected(ref("Chevrolet", "Cruze", "1.8", "6T30"), "CHEVROLET CRUZE 1.4 TURBO")
        self.assertRejected(ref("Fiat", "Toro", "1.3T AT6", "Aisin 6AT"), "FIAT TORO 1.8 - CAJA AT6")

    def test_distinta_cantidad_de_marchas(self):
        self.assertRejected(ref("Ford", "Focus", "2.0", "6F35"), "FORD FOCUS 2.0 ZETEC 4 MARCHAS")
        self.assertRejected(ref("Mercedes", "C250", "2.0", "9G-Tronic"), "MERCEDES BENZ C250 CGI 7G-TRONIC")
        self.assertRejected(ref("Jeep", "Renegade", "1.8", "ZF 9HP"), "JEEP RENEGADE 1.8 AT6")
        self.assertRejected(ref("Ford", "Ranger", "3.0 V6", "10R80"), "FORD RANGER - CAJA 6R80")

    def test_distinto_tipo_de_caja(self):
        self.assertRejected(ref("Audi", "A3", "1.4 TFSI Tiptronic", "Aisin 6AT"), "AUDI A3 1.4 TFSI S-TRONIC")
        self.assertRejected(ref("Audi", "A4", "2.0 TFSI", "DL382", "DSG"), "AUDI A4 B8 2.0 TFSI ZF8HP")

    def test_modelo_hermano_mas_especifico(self):
        siblings = {frozenset({"C4"}), frozenset({"C4", "LOUNGE"})}
        self.assertRejected(
            ref("Citroën", "C4", "2.0", "AL4"),
            "CITROEN C4 LOUNGE 1.6 / 2.0 THP TIPTRONIC",
            siblings,
        )

    def test_numeros_sueltos_no_cuentan(self):
        # "2.0" no debe coincidir con cualquier "2" del texto.
        self.assertRejected(ref("Jeep", "Compass", "2.0 Diesel", "ZF 9HP"), "JEEP COMPASS 2.4 - CAJA AT6")


class AcceptsGoodMatches(unittest.TestCase):
    def test_coincidencia_alta(self):
        best, confidence, reason = choose_match(
            ref("Chevrolet", "Cruze", "1.4T", "6T40", liters=9.0),
            [shop("CHEVROLET CRUZE 1.4 TURBO", liters=10.0)],
        )
        self.assertIsNotNone(best)
        self.assertEqual(confidence, "ALTA")
        self.assertEqual(reason, "")

    def test_codigo_generico_queda_pendiente(self):
        _, _, reason = choose_match(
            ref("Chevrolet", "Spin", "1.8", "6AT"),
            [shop("CHEVROLET SPIN 1.8")],
        )
        self.assertIn("genérico", reason)


if __name__ == "__main__":
    unittest.main()
